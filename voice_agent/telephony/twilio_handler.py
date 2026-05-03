"""Twilio telephony handler — manages call lifecycle and media streams."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class TwilioCallManager:
    """Manages Twilio outbound calls with media stream WebSocket."""

    def __init__(self) -> None:
        from twilio.rest import Client as TwilioClient

        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.phone_from = os.getenv("TWILIO_PHONE_NUMBER", "")

        if account_sid and auth_token:
            self.client = TwilioClient(account_sid, auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials missing — call initiation disabled")

        self.active_calls: dict[str, Any] = {}

    def generate_twiml(self, ws_url: str) -> str:
        """Generate TwiML to connect a call to our WebSocket media stream."""
        from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

        resp = VoiceResponse()
        connect = Connect()
        stream = Stream(url=ws_url)
        connect.append(stream)
        resp.append(connect)
        return str(resp)

    def make_call(self, to_number: str, lead_id: str, ws_base_url: str) -> dict | None:
        """Initiate an outbound call to a lead."""
        if not self.client:
            logger.error("Cannot make call: Twilio client not configured")
            return None

        ws_url = f"{ws_base_url}/media-stream?lead_id={lead_id}"

        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_from,
                twiml=self.generate_twiml(ws_url),
                status_callback=f"{ws_base_url}/call-status",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                status_callback_method="POST",
            )
            self.active_calls[call.sid] = {
                "sid": call.sid,
                "lead_id": lead_id,
                "status": call.status,
                "to": to_number,
            }
            logger.info("Call initiated: %s → %s", call.sid, to_number)
            return {"call_sid": call.sid, "status": call.status, "to": to_number}
        except Exception as e:
            logger.error("Failed to initiate call: %s", e)
            return None

    def update_call_status(self, call_sid: str, status: str) -> None:
        """Update call status from Twilio callback."""
        if call_sid in self.active_calls:
            self.active_calls[call_sid]["status"] = status
        logger.info("Call %s status: %s", call_sid, status)
