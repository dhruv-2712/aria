# ARIA — Autonomous Research & Intelligence Architecture

> An 8-agent autonomous AI system that transforms any research question into a
> publication-quality, multi-format report in under 90 seconds.

![Pipeline](https://img.shields.io/badge/agents-8-6c63ff?style=flat-square)
![Stack](https://img.shields.io/badge/stack-Python%20%7C%20FastAPI%20%7C%20Groq%20%7C%20SQLite-a78bfa?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)

---

## What ARIA Does

You type a research question. ARIA autonomously:

1. Searches and gathers findings from multiple angles
2. Classifies them across 8 domains and fills coverage gaps
3. Extracts insights and maps relationships between ideas
4. Critiques every claim with counterarguments
5. Synthesizes cross-domain connections humans would miss
6. Plans the optimal report structure
7. Generates 3 publication-quality report formats simultaneously

No human in the loop. No manual steps. One query → full research report.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (Agent 1)                  │
│         Master controller · retry queue · global state      │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │                           │
    ┌────▼─────┐              ┌──────▼──────┐
    │RESEARCHER│◄─────────────│ CLASSIFIER  │
    │ Agent 2  │  gap-fill    │  Agent 3    │
    │          │  loop ×2     │             │
    └────┬─────┘              └──────┬──────┘
         │                           │
         └──────────┬────────────────┘
                    │ all findings
                    ▼
             ┌──────────────┐
             │   ANALYST    │
             │   Agent 4    │
             │ insight map  │
             └──────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ DEVIL'S ADVOCATE│◄──── revision loop ×2
          │    Agent 5      │────► back to Analyst
          │  critiques all  │      if weak > 30%
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  SYNTHESIZER    │
          │    Agent 6      │
          │ cross-domain    │
          │  connections    │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │   VISUALIZER    │
          │    Agent 7      │
          │ structure plan  │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │     WRITER      │
          │    Agent 8      │◄── parallel generation
          │  3 formats      │    (executive + standard
          └────────┬────────┘     + technical)
                   │
                   ▼
         ┌──────────────────┐
         │   FINAL REPORT   │
         │ Executive (400w) │
         │ Standard (2000w) │
         │ Technical Appendix│
         │ Citations list   │
         └──────────────────┘
```

---

## Agent Specifications

| # | Agent | Role | Key Behaviour |
|---|---|---|---|
| 1 | **Orchestrator** | Master controller | Retry queue, global state, loop management |
| 2 | **Researcher** | Web intelligence | 3+ search angles, confidence scoring |
| 3 | **Classifier** | Domain taxonomy | 8 domains, gap detection, research loops |
| 4 | **Analyst** | Insight extraction | Relationship graph, confidence scoring |
| 5 | **Devil's Advocate** | Adversarial critic | Counterarguments, fallacy detection, revision trigger |
| 6 | **Synthesizer** | Cross-domain synthesis | Non-obvious connections, headline finding |
| 7 | **Visualizer** | Content architecture | Section planning, executive summary |
| 8 | **Writer** | Report generation | 3 formats in parallel, citation formatting |

---

## Intelligence Features

**Adversarial critique loop** — Devil's Advocate scores every claim as
strong/moderate/weak/unverified. If weak claims exceed 30% of total,
it triggers an automatic revision request back to the Analyst. Max 2 loops.

**Research gap filling** — Classifier identifies domains with fewer than 2
findings and sends targeted follow-up queries back to the Researcher.
Max 2 loops to prevent infinite recursion.

**Cross-domain synthesis** — Synthesizer finds non-obvious connections
between different domains (e.g. economic insight linking to ethical insight)
that specialist agents would miss individually.

**Query caching** — Identical queries within 24 hours return cached findings
instantly, skipping the research phase entirely.

**Parallel report generation** — All 3 report formats are generated
simultaneously using ThreadPoolExecutor, cutting Writer time by ~60%.

---

## Report Formats

### Executive Report (300–400 words)
Business-friendly, zero jargon. Starts with the single most important finding,
includes 2–3 actionable implications, ends with a bottom line.

### Standard Report (1500–2000 words)
Structured sections with markdown formatting. Covers all domains, cross-domain
analysis, implications and outlook. Suitable for academic or professional use.

### Technical Appendix
Raw findings with confidence scores, source URLs, methodology notes,
insight inventory, and full pipeline confidence metrics.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM Backend | Groq API (Llama 3.1 — free tier, 14,400 req/day) |
| API Framework | FastAPI + Uvicorn |
| Database | SQLite (sessions, agent logs, reports, findings) |
| Frontend | Vanilla HTML/CSS/JS — no framework |
| Agent Orchestration | Custom Python — sequential + parallel |
| State Management | Python dataclasses (ARIAState) |

---

## Project Structure

```
aria/
├── main.py                  # FastAPI entry point (4 endpoints)
├── orchestrator.py          # Agent 1 — master controller
├── agents/
│   ├── researcher.py        # Agent 2 — web intelligence
│   ├── classifier.py        # Agent 3 — domain taxonomy
│   ├── analyst.py           # Agent 4 — insight extraction
│   ├── devil.py             # Agent 5 — adversarial critic
│   ├── synthesizer.py       # Agent 6 — cross-domain synthesis
│   ├── visualizer.py        # Agent 7 — content architecture
│   └── writer.py            # Agent 8 — report generation
├── core/
│   ├── state.py             # ARIAState dataclass
│   ├── gemini_client.py     # Groq API wrapper (named for compatibility)
│   ├── memory.py            # SQLite layer — logging + caching
│   └── router.py            # Inter-agent routing
├── db/
│   └── aria.db              # SQLite database (auto-created)
├── frontend/
│   ├── index.html           # Single-page UI
│   ├── style.css            # Dark theme
│   └── app.js               # Pipeline visualiser + report renderer
└── requirements.txt
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/dhruv-2712/aria.git
cd aria
pip install -r requirements.txt
```

### 2. Get a free Groq API key

Sign up at [console.groq.com](https://console.groq.com) — free, no card needed,
14,400 requests/day.

### 3. Set up environment

```bash
# Create .env file
echo "GROQ_API_KEY=your_key_here" > .env
```

### 4. Run

```bash
python -m uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/research` | Start a new research job |
| `GET` | `/status/{session_id}` | Poll job status |
| `GET` | `/report/{session_id}` | Get final report |
| `GET` | `/logs/{session_id}` | Get agent execution logs |
| `GET` | `/health` | API health check |

### Example

```bash
# Start research
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Impact of quantum computing on cryptography"}'

# Response
{
  "session_id": "abc123",
  "message": "Research job started",
  "query": "Impact of quantum computing on cryptography"
}

# Poll status
curl http://localhost:8000/status/abc123

# Get report when done
curl http://localhost:8000/report/abc123
```

---

## Database Schema

```sql
sessions      -- id, query, created_at, status
agent_logs    -- session_id, agent_name, input_json, output_json, duration_ms
reports       -- session_id, executive, standard, technical, citations_json
findings      -- session_id, content, source_url, confidence, domain
```

Every agent call is logged with full input/output JSON and duration.
Complete pipeline observability out of the box.

---

## Requirements

```
groq
fastapi
uvicorn[standard]
python-dotenv
pydantic
```

No GPU required. Runs entirely on CPU via Groq's cloud inference.

---

## Sample Output

For query: *"Impact of quantum computing on cryptography"*

```
✅ 35 findings gathered
✅ 10 insights extracted  
✅ 81% pipeline confidence
✅ 5 cross-domain connections
✅ Executive + Standard + Technical reports generated
✅ Citations compiled
```

