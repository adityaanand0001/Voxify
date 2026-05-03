<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/LangGraph-orchestration-6366f1?style=for-the-badge" alt="LangGraph">
  <img src="https://img.shields.io/badge/Gemini-reasoning-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/ElevenLabs-TTS-7c3aed?style=for-the-badge" alt="ElevenLabs">
  <img src="https://img.shields.io/badge/Whisper-STT-412991?style=for-the-badge&logo=openai&logoColor=white" alt="Whisper">
  <img src="https://img.shields.io/badge/Twilio-telephony-F22F46?style=for-the-badge&logo=twilio&logoColor=white" alt="Twilio">
</p>

<p align="center">
  <h1 align="center">&#127908; Voxify</h1>
  <p align="center"><em>Your pipeline, amplified.</em></p>
</p>

---

**Voxify** is a production-grade AI voice agent that makes real outbound sales calls. It listens, understands context, extracts qualification signals, handles objections, scores leads in real time, and books meetings — all while sounding completely human.

> Not a chatbot. Not a demo. A **decision engine with a voice interface**.

---

## &#127756; Architecture

```
Twilio Call
  └─ WebSocket Media Stream
       └─ Audio Ingestion Server
            ├─ Streaming STT (Whisper)
            │
            ┌──────────────────────────────────┐
            │    LangGraph Decision Engine      │
            │                                   │
            │   analyze ──► score ──► respond   │
            │       │           │          │     │
            │    Gemini      Scoring    Gemini  │
            │   (semantic   (weighted   (biz-   │
            │   analysis)   factors)   aware)   │
            │                                   │
            │   sentiment & stage               │
            │   budget & timeline               │
            │   authority & need                │
            │   objection detection             │
            │                                   │
            │         ┌── action ──┐            │
            │         │  BOOK /    │            │
            │         │  FOLLOWUP  │            │
            │         │  NURTURE / │            │
            │         │  DROP      │            │
            │         └────────────┘            │
            └──────────────────────────────────┘
                       │
            Streaming TTS (ElevenLabs)
                       │
                  Back to Twilio
```

---

## &#9889; Features

| Category | Capability |
|----------|-----------|
| **Semantic Understanding** | Gemini-powered analysis of every utterance — not keyword matching |
| **Real-time Scoring** | 6-factor composite score recalculated on every turn |
| **Stage Detection** | greeting → discovery → qualification → booking progression |
| **Objection Handling** | 5 objection types with AI-crafted responses from your playbook |
| **Business Context** | Configurable identity — change name, product, pricing, guardrails in one file |
| **Decision Engine** | BOOK_MEETING / STRONG_FOLLOWUP / NURTURE / DROP with warm-up guard |
| **Streaming TTS** | ElevenLabs voice synthesis with <500ms latency |
| **Streaming STT** | Local Whisper transcription from audio chunks |
| **Twilio Integration** | WebSocket media streams for real-time bidirectional audio |
| **CRM Ready** | Supabase persistence — call logs, lead updates, booking records |

---

## &#129504; Decision Engine

Voxify doesn't just transcribe calls — it **understands** them.

### The Scoring Formula

| Factor | Weight | Signal |
|--------|--------|--------|
| Budget | 25% | Dollar amount extracted from conversation |
| Timeline | 20% | Urgency — immediate to 6+ months |
| Authority | 15% | decision_maker / influencer / researcher |
| Need Level | 20% | Pain point clarity (semantic analysis) |
| Engagement | 10% | Interaction quality and interest signals |
| Sentiment | 10% | Emotional tone — positive / neutral / negative |

```
score = (budget × 0.25 + timeline × 0.20 + authority × 0.15
       + need × 0.20 + engagement × 0.10 + sentiment × 0.10) × 100
```

### Decision Thresholds

| Score | Decision | Action |
|-------|----------|--------|
| ≥ 80 | `BOOK_MEETING` | Suggest specific day/time on the call |
| ≥ 60 | `STRONG_FOLLOWUP` | Secure follow-up commitment |
| ≥ 40 | `NURTURE` | Keep warm, ask discovery questions |
| < 40 | `DROP` | End gracefully (only after 4+ turns or explicit rejection) |

### Warm-up Guard

The engine **never drops a lead in the first 4 turns** unless the prospect explicitly rejects. ""Hi, who's this?" won't trigger a drop — the agent keeps the conversation going.

---

## &#128640; Quick Start

```bash
# 1. Clone
git clone https://github.com/adityaanand0001/Voxify.git
cd Voxify

# 2. Install
pip install -r voice_agent/requirements.txt

# 3. Configure
cp voice_agent/.env.example voice_agent/.env
# Edit .env — set GEMINI_API_KEY (required for semantic mode)

# 4. Test the scoring engine (no API keys needed)
python voice_agent/main.py test

# 5. Simulate a full conversation
python voice_agent/main.py simulate

# 6. Start the live call server
python voice_agent/main.py serve
```

---

## &#128230; Project Structure

```
Voxify/
├── voice_agent/
│   ├── main.py                    # CLI entry: serve | test | simulate
│   │
│   ├── config/
│   │   └── business_context.py    # ★ Edit this to change agent/brand/pricing
│   │
│   ├── state/
│   │   └── schema.py              # CallState dataclass (budget, timeline, etc.)
│   │
│   ├── scoring/
│   │   └── scoring.py             # 6-factor scoring + decision engine
│   │
│   ├── agents/
│   │   └── listener.py            # UnifiedAnalyzer + ResponseGenerator
│   │                              #   (Gemini-first, regex fallback)
│   │
│   ├── graph/
│   │   ├── graph_builder.py       # LangGraph: analyze → score → respond → act
│   │   └── nodes.py               # Node exports
│   │
│   ├── stt/
│   │   └── whisper_stream.py      # Streaming Whisper transcription
│   │
│   ├── tts/
│   │   └── elevenlabs_stream.py   # Streaming ElevenLabs voice synthesis
│   │
│   ├── telephony/
│   │   ├── twilio_handler.py      # Twilio call manager
│   │   └── websocket_server.py    # Media stream ↔ graph bridge
│   │
│   ├── db/
│   │   └── models.py              # Supabase persistence layer
│   │
│   └── .env.example               # Environment template
│
└── test_validation.py             # 27-test validation suite
```

---

## ⚙ Configuration

### Environment (.env)

```env
GEMINI_API_KEY=sk-...           # Primary: Gemini for semantic analysis
ELEVENLABS_API_KEY=...          # TTS voice synthesis
TWILIO_ACCOUNT_SID=...          # Telephony provider
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
SUPABASE_URL=...                # CRM / database
SUPABASE_ANON_KEY=...
```

### Business Context (`config/business_context.py`)

```python
@dataclass
class BusinessContext:
    agent_name: str = "Aria"          # What the AI calls itself
    company_name: str = "Voxify"      # Company it represents
    product_name: str = "Voxify Voice Agent"
    value_proposition: str = "..."    # The pitch
    pricing_tiers: list[dict] = [...]  # Your plans
    objection_responses: dict = {...}  # How to handle pushback
    do_not_say: list[str] = [...]     # Guardrails
    # ... 20+ configurable fields
```

Change anything in this file and the agent adapts — no prompt engineering required.

---

## &#127916; Simulation (no API keys needed)

```bash
$ python voice_agent/main.py simulate

  Turn 1 | greeting
    User:    "Hi, who's this?"
    Agent:   "Hi Mark, this is Aria from Voxify. How are you doing today?"
    Score:   23.0 → NURTURE

  Turn 2 | qualification
    User:    "I handle procurement for our team. We need something like this."
    Agent:   "Could you tell me more about what you're looking for?"
    Score:   38.0 → NURTURE

  Turn 3 | qualification
    User:    "Budget is around 75k, we need it live within 2 months."
    Agent:   "That's great. Let me follow up with details on how Voxify can help."
    Score:   68.0 → STRONG_FOLLOWUP

  Turn 6 | booking
    User:    "Okay, let's set up a call for next week."
    Agent:   "Based on what you've shared, let's get something on the calendar.
              How does Tuesday look?"
    Score:   82.0 → BOOK_MEETING
```

*(Responses above use emergency fallback mode. With `GEMINI_API_KEY`, every turn gets unique, contextual responses.)*

---

## &#9989; Validation

```bash
$ python test_validation.py

=== Scoring Engine ===
  [PASS] Hot lead → BOOK_MEETING
  [PASS] Warm lead → STRONG_FOLLOWUP
  [PASS] Cold lead → DROP

=== Budget Extraction ===
  [PASS] "50k budget" → 50000
  [PASS] "$75,000" → 75000

=== Timeline & Authority ===
  [PASS] "ASAP" → IMMEDIATE
  [PASS] "I decide" → DECISION_MAKER
  [PASS] "run it by my boss" → INFLUENCER

=== Objection Handling ===
  [PASS] Score drops on objection
  [PASS] Not dropped in first 4 turns

=== LangGraph Compilation ===
  [PASS] 4-node graph compiles

Results: 27 passed, 0 failed
```

---

## &#128295; Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Orchestration | [LangGraph](https://www.langchain.com/langgraph) | State machine, decision routing |
| Reasoning | [Google Gemini](https://ai.google.dev/) | Semantic understanding, response generation |
| STT | [OpenAI Whisper](https://github.com/openai/whisper) | Streaming speech-to-text |
| TTS | [ElevenLabs](https://elevenlabs.io/) | Streaming text-to-speech |
| Telephony | [Twilio](https://www.twilio.com/) | Call management, media streams |
| Database | [Supabase](https://supabase.com/) | Lead storage, call logs, bookings |
| Config | [Pydantic](https://docs.pydantic.dev/) | Business context, state validation |

---

## &#128295; Roadmap

- [ ] Multi-language support (Spanish, German, French)
- [ ] Sentiment-based dynamic voice tone adjustment
- [ ] Call recording + post-call analysis summary
- [ ] A/B testing different sales scripts
- [ ] Slack/email notifications for hot leads
- [ ] Dashboard UI for monitoring live calls
- [ ] Docker deployment with one-command launch
- [ ] Cal.com / HubSpot native booking integration

---

<p align="center">
  <sub>Built with LangGraph + Gemini + ElevenLabs + Twilio</sub><br>
  <sub>MIT License · <a href="https://github.com/adityaanand0001/Voxify">github.com/adityaanand0001/Voxify</a></sub>
</p>
