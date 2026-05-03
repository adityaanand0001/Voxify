<div align="center">
  <br>
  <pre style="font-family: monospace; font-size: 14px; line-height: 1.2;">
██╗   ██╗ ██████╗ ██╗  ██╗██╗███████╗██╗   ██╗
██║   ██║██╔═══██╗╚██╗██╔╝██║██╔════╝╚██╗ ██╔╝
██║   ██║██║   ██║ ╚███╔╝ ██║█████╗   ╚████╔╝ 
╚██╗ ██╔╝██║   ██║ ██╔██╗ ██║██╔══╝    ╚██╔╝  
 ╚████╔╝ ╚██████╔╝██╔╝ ██╗██║██║        ██║   
  ╚═══╝   ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   
  </pre>
  <h3>⚡ An AI Agent That Closes Deals Over Voice ⚡</h3>
  <br>
  <p>
    <img src="https://img.shields.io/badge/AI_Agent-Autonomous-8B5CF6?style=for-the-badge&logo=openai&logoColor=white">
    <img src="https://img.shields.io/badge/LangGraph-State_Machine-6366f1?style=for-the-badge">
    <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white">
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white">
    <br>
    <img src="https://img.shields.io/badge/ElevenLabs-TTS-7c3aed?style=for-the-badge">
    <img src="https://img.shields.io/badge/Whisper-STT-412991?style=for-the-badge&logo=openai&logoColor=white">
    <img src="https://img.shields.io/badge/Twilio-Telephony-F22F46?style=for-the-badge&logo=twilio&logoColor=white">
    <img src="https://img.shields.io/badge/Supabase-CRM-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white">
  </p>
</div>

---

# 🤖 Voxify — The Autonomous Voice Sales Agent

**Voxify is not a chatbot. It's not a demo. It's an AI agent that makes real sales calls, thinks on its feet, and books meetings — completely autonomously.**

> An **AI agent** perceives, reasons, decides, and acts. Voxify does all four — over a live phone call, in real time. It listens through Whisper, reasons through Gemini + LangGraph, scores every lead on a 6-factor model, generates natural responses, and speaks through ElevenLabs. Every decision is its own.

<br>

## 🧠 What Makes It An Agent

| Agent Capability | How Voxify Does It |
|:---|:---|
| **Perceive** | Streaming Whisper STT transcribes audio in real time |
| **Reason** | Gemini 2.0 Flash analyzes every utterance — sentiment, intent, objection type |
| **Decide** | 6-factor weighted scoring engine decides BOOK / FOLLOWUP / NURTURE / DROP |
| **Act** | ElevenLabs TTS speaks the response; Twilio bridges the call |
| **Learn** | LangGraph state machine tracks full conversation context across turns |
| **Tools** | CRM persistence (Supabase), call routing (Twilio), calendar booking |

<br>

## 🏗 Architecture

```
                    ┌─────────────────────────────┐
                    │         TWILIO CLOUD         │
                    │   +1-XXX-XXX-XXXX            │
                    └──────────┬──────────────────┘
                               │ WebSocket Media Stream
                               ▼
              ┌─────────────────────────────────┐
              │     AUDIO INGESTION SERVER       │
              │  (WebSocket ↔ Streaming Audio)   │
              └──────┬──────────────┬───────────┘
                     │              │
              ┌──────▼──────┐  ┌───▼────────────┐
              │   WHISPER   │  │   ELEVENLABS    │
              │  (STT In)   │  │   (TTS Out)     │
              └──────┬──────┘  └───▲────────────┘
                     │              │
                     ▼              │
         ┌───────────────────────────────────────┐
         │                                       │
         │     LANGGRAPH AGENT ORCHESTRATOR      │
         │                                       │
         │  ┌──────────┐    ┌──────────────────┐ │
         │  │ ANALYZE  │    │                  │ │
         │  │ (Gemini) ├───►│     SCORING      │ │
         │  └──────────┘    │  6-factor model  │ │
         │                  └────────┬─────────┘ │
         │                           │           │
         │  ┌──────────┐    ┌───────▼─────────┐ │
         │  │  ACTION  │◄───┤    RESPONSE     │ │
         │  │  BOOK /  │    │    (Gemini)     │ │
         │  │ FOLLOWUP │    └─────────────────┘ │
         │  │ NURTURE  │                        │
         │  │   DROP   │                        │
         │  └──────────┘                        │
         └───────────────────────────────────────┘
                     │
                     ▼
              ┌─────────────┐
              │   SUPABASE  │
              │  (CRM/DB)   │
              └─────────────┘
```

<br>

## ⚙ The Agent's Decision Loop

Every turn of the conversation goes through 4 nodes:

| # | Node | What Happens |
|:--|:-----|:---|
| 1 | **analyze** | Gemini reads the full transcript. Extracts sentiment, engagement level, budget, timeline, authority, need, and objection flags. One LLM call per turn. |
| 2 | **scoring** | 6-factor composite score computed. Thresholds map score → decision. |
| 3 | **response** | Gemini generates a contextual, business-aware response (max 2 sentences). |
| 4 | **action** | Executes the decision. Books meeting, schedules follow-up, or ends call with warm-up guard. |

<br>

## 📊 The Scoring Engine

Voxify doesn't guess — it scores every lead against a weighted model recalculated on **every turn**.

| Factor | Weight | What It Measures |
|:---|:---:|:---|
| **Budget** | 25% | Dollar amount extracted from conversation (`$50k`, `$75,000`) |
| **Need** | 20% | Pain point clarity — how badly they need this (Gemini semantic analysis) |
| **Timeline** | 20% | Urgency — `immediate` → `6+ months` |
| **Authority** | 15% | Who's talking — `decision_maker` / `influencer` / `researcher` |
| **Engagement** | 10% | Are they leaning in or brushing off? |
| **Sentiment** | 10% | Emotional tone — `positive` / `neutral` / `negative` |

```
score = (budget×0.25 + need×0.20 + timeline×0.20 + authority×0.15 + engagement×0.10 + sentiment×0.10) × 100
```

### Decision Thresholds

| Score | Decision | Agent's Action |
|:---:|:---|:---|
| ≥ 80 | **BOOK_MEETING** | Suggest specific day/time, share calendar link |
| ≥ 60 | **STRONG_FOLLOWUP** | Secure commitment, schedule callback |
| ≥ 40 | **NURTURE** | Keep warm, ask discovery questions |
| < 40 | **DROP** | End politely (only after 4+ turns or explicit rejection) |

> **Warm-up guard**: The agent never drops in the first 4 turns. Someone saying *"Hi, who's this?"* won't kill the call.

<br>

## 🎯 Objection Handling

The agent detects 5 objection types and responds with business-context-aware counters:

| Objection | Trigger | Agent's Response |
|:---|:---|:---|
| **price** | Budget concerns | "ROI pays for itself in the first month. Free trial?" |
| **not_interested** | Cold rejection | "Totally understand — worth 2 minutes to see if this saves 10+ hrs/week?" |
| **competitor** | Using another solution | "Great — we specialize in the outbound voice channel specifically." |
| **timing** | Not now | "When's better? I'll send context in the meantime." |
| **gatekeeper** | Wrong person | "Could you point me to the right person? I'll send a note instead." |

All objection responses live in `config/business_context.py` — change them without touching the agent code.

<br>

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/adityaanand0001/Voxify.git
cd Voxify

# Install
pip install -r voice_agent/requirements.txt

# Configure
cp voice_agent/.env.example voice_agent/.env
# Add your GEMINI_API_KEY (required for full agent mode)

# Test the scoring engine (no API keys needed)
python voice_agent/main.py test

# Simulate a full conversation through the agent graph
python voice_agent/main.py simulate

# Launch the live call server
python voice_agent/main.py serve
```

<br>

## 🎬 Simulation Demo

```bash
$ python voice_agent/main.py simulate

  Turn 1 | greeting
    User:    "Hi, who's this?"
    Agent:   "Hi Mark, this is Aria from Voxify. How are you doing today?"
    Score:   23.0  →  NURTURE

  Turn 2 | discovery
    User:    "I handle procurement for our team. We need something like this."
    Agent:   "Could you tell me more about what you're looking for?"
    Score:   38.0  →  NURTURE

  Turn 3 | qualification
    User:    "Budget is around 75k, we need it live within 2 months."
    Agent:   "That's great. Let me follow up with details on how Voxify can help."
    Score:   68.0  →  STRONG_FOLLOWUP

  Turn 6 | booking
    User:    "Okay, let's set up a call for next week."
    Agent:   "Based on what you've shared, let's get something on the calendar.
              How does Tuesday look?"
    Score:   82.0  →  BOOK_MEETING
```

*(Above uses emergency fallback responses. With `GEMINI_API_KEY`, every turn gets unique, contextual responses.)*

<br>

## 🧪 Validation Suite

```bash
$ python test_validation.py

=== Scoring Engine ===
  [PASS] Hot lead (60k, immediate, decision maker)  →  BOOK_MEETING
  [PASS] Warm lead decision                          →  STRONG_FOLLOWUP
  [PASS] Cold lead decision                          →  DROP

=== Budget Extraction ===
  [PASS] "50k budget"                                →  50000
  [PASS] "$75,000"                                   →  75000
  [PASS] "25 thousand dollars"                       →  25000

=== Timeline & Authority ===
  [PASS] "ASAP"                                      →  IMMEDIATE
  [PASS] "I decide"                                  →  DECISION_MAKER
  [PASS] "run it by my boss"                         →  INFLUENCER

=== Objection Handling ===
  [PASS] Score drops after objection
  [PASS] Objection recorded correctly

=== LangGraph Compilation ===
  [PASS] 4-node agent graph compiles

Results: 27 passed, 0 failed ✓
```

<br>

## 📁 Project Structure

```
Voxify/
├── voice_agent/
│   ├── main.py                    # CLI: serve | test | simulate
│   │
│   ├── agents/
│   │   └── listener.py            # UnifiedAnalyzer + ResponseGenerator (Gemini)
│   │
│   ├── graph/
│   │   ├── graph_builder.py       # LangGraph: analyze → score → respond → act
│   │   └── nodes.py               # Node exports
│   │
│   ├── scoring/
│   │   └── scoring.py             # 6-factor scoring + decision engine
│   │
│   ├── config/
│   │   └── business_context.py    # ⭐ Edit this to change agent identity
│   │
│   ├── state/
│   │   └── schema.py              # CallState dataclass + enums
│   │
│   ├── stt/
│   │   └── whisper_stream.py      # Streaming Whisper transcription
│   │
│   ├── tts/
│   │   └── elevenlabs_stream.py   # Streaming ElevenLabs TTS
│   │
│   ├── telephony/
│   │   ├── twilio_handler.py      # Twilio call manager
│   │   └── websocket_server.py    # Media stream ↔ graph bridge
│   │
│   ├── db/
│   │   └── models.py              # Supabase persistence
│   │
│   └── .env.example
│
└── test_validation.py             # 27 tests
```

<br>

## 🔧 Configuration

### Environment (.env)

```env
GEMINI_API_KEY=sk-...              # Primary: semantic analysis & reasoning
ELEVENLABS_API_KEY=...             # Voice synthesis
TWILIO_ACCOUNT_SID=...             # Call provider
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
SUPABASE_URL=...                   # CRM / lead database
SUPABASE_ANON_KEY=...
```

### Business Context (`config/business_context.py`)

This is the single source of truth for your agent's identity. Change anything here and the agent adapts — no prompt engineering needed:

```python
@dataclass
class BusinessContext:
    agent_name: str = "Aria"                 # What the agent calls itself
    company_name: str = "Voxify"             # Who it represents
    value_proposition: str = "..."           # The pitch
    pricing_tiers: list[dict] = [...]        # Your plans
    objection_responses: dict = {...}        # Counter-playbook
    do_not_say: list[str] = [...]            # Guardrails
    calendar_link: str = "..."               # Booking link
    call_flow: list[str] = [...]             # Conversation structure
    # ... 20+ configurable fields
```

<br>

## 🛠 Tech Stack

| Layer | Technology | Role |
|:---|:---|:---|
| **Agent Orchestration** | [LangGraph](https://www.langchain.com/langgraph) | State machine, decision routing, turn management |
| **Reasoning** | [Google Gemini 2.0 Flash](https://ai.google.dev/) | Semantic understanding, response generation |
| **Speech-to-Text** | [OpenAI Whisper](https://github.com/openai/whisper) | Streaming transcription from audio chunks |
| **Text-to-Speech** | [ElevenLabs](https://elevenlabs.io/) | Real-time voice synthesis (<500ms latency) |
| **Telephony** | [Twilio](https://www.twilio.com/) | Call management, WebSocket media streams |
| **Database** | [Supabase](https://supabase.com/) | Lead CRUD, call logs, booking persistence |
| **Config** | [Pydantic](https://docs.pydantic.dev/) | Business context & state validation |

<br>

## 🗺 Roadmap

- [ ] Multi-language support (Spanish, German, French, Hindi)
- [ ] Sentiment-driven dynamic voice tone (pace, pitch, warmth)
- [ ] Post-call AI summary + email to rep
- [ ] A/B testing different sales scripts and personas
- [ ] Slack/email alerts for hot leads (score ≥ 80)
- [ ] Live dashboard for monitoring active calls
- [ ] Docker one-command deploy
- [ ] Native Cal.com / HubSpot booking integration
- [ ] Voice cloning for branded agent personas
- [ ] Multi-agent handoff (qualifier → closer)

<br>

---

<div align="center">
  <p>
    <sub>
      Built with LangGraph + Gemini + ElevenLabs + Twilio + Supabase<br>
      MIT License · <a href="https://github.com/adityaanand0001/Voxify"><b>github.com/adityaanand0001/Voxify</b></a>
    </sub>
  </p>
</div>
