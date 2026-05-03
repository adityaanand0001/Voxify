"""Database models for AI Sales Call Agent — PostgreSQL via Supabase."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from supabase import create_client


class Database:
    """Thin wrapper around Supabase client for call agent storage."""

    def __init__(self) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        self.client = create_client(supabase_url, supabase_key)

    # ── Leads ──────────────────────────────────────────────────────────

    def get_lead(self, lead_id: str) -> dict | None:
        resp = self.client.table("leads").select("*").eq("id", lead_id).limit(1).execute()
        rows = resp.data or []
        return rows[0] if rows else None

    def get_leads_to_call(self, limit: int = 10) -> list[dict]:
        resp = (
            self.client.table("leads")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return resp.data or []

    # ── Call logs ──────────────────────────────────────────────────────

    def log_call(self, call_data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "lead_id": call_data["lead_id"],
            "call_sid": call_data.get("call_sid", ""),
            "duration_seconds": call_data.get("duration", 0),
            "lead_score": call_data.get("lead_score", 0),
            "decision": call_data.get("decision", "NURTURE"),
            "stage_reached": call_data.get("stage", "greeting"),
            "transcript": call_data.get("transcript", ""),
            "extracted_data": call_data.get("extracted", {}),
            "created_at": now,
        }
        resp = self.client.table("call_logs").insert(record).execute()
        return (resp.data or [{}])[0]

    # ── Update lead after call ─────────────────────────────────────────

    def update_lead_after_call(self, lead_id: str, score: float, decision: str) -> None:
        self.client.table("leads").update({
            "lead_score": score,
            "decision": decision,
            "last_called_at": datetime.now(timezone.utc).isoformat(),
            "status": "contacted",
        }).eq("id", lead_id).execute()

    # ── Booking ────────────────────────────────────────────────────────

    def create_booking(self, lead_id: str, booking_data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "lead_id": lead_id,
            "scheduled_at": booking_data.get("scheduled_at", now),
            "status": "confirmed",
            "notes": booking_data.get("notes", ""),
            "created_at": now,
        }
        resp = self.client.table("bookings").insert(record).execute()
        return (resp.data or [{}])[0]
