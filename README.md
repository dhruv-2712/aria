# Autonomous Research & Intelligence Architecture

**One query. Eight agents. A publication-quality report.**

[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-f55036?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Render-6c63ff?style=flat-square&logo=render&logoColor=white)](https://aria-emh3.onrender.com)

**[→ Try the live demo](https://aria-emh3.onrender.com)**
*Free tier — may take ~15s to wake from sleep*

</div>

---

## What is ARIA?

ARIA is a multi-agent research pipeline that takes a question and autonomously produces an exhaustive intelligence report. It doesn't just summarise — it gathers raw findings, classifies them across domains, extracts structured insights, stress-tests every claim with counterarguments, synthesizes cross-domain connections, and writes three distinct report formats in parallel.

No prompt engineering. No manual steps. One input → complete research output.

---

## Pipeline

```
                         ┌─────────────────────────────────┐
                         │            ORCHESTRATOR          │
                         │   retry logic · state · loops   │
                         └──────────────┬──────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │  gap-fill loop ×2  │
                    ▼                   ▼                    │
             ┌────────────┐    ┌──────────────┐             │
             │ RESEARCHER │───▶│  CLASSIFIER  │─────────────┘
             │  Agent 02  │    │   Agent 03   │
             │            │    │ 8-domain map │
             └────────────┘    └──────┬───────┘
                                      │ all findings
                                      ▼
                               ┌─────────────┐
                               │   ANALYST   │
                               │  Agent 04   │
                               │ insight map │
                               └──────┬──────┘
                                      │
                          ┌───────────┤  revision loop ×2
                          ▼           │
                  ┌──────────────┐    │ if weak > 30%
                  │   DEVIL'S   │────▶│ re-run analyst
                  │   ADVOCATE  │    │
                  │   Agent 05  │────┘
                  └──────┬──────┘
                         │
              ┌──────────┴──────────┐  (parallel)
              ▼                     ▼
     ┌──────────────────┐  ┌────────────────┐
     │   SYNTHESIZER    │  │   VISUALIZER   │
     │    Agent 06      │  │    Agent 07    │
     │ cross-domain     │  │ structure plan │
     │ connections      │  │                │
     └────────┬─────────┘  └───────┬────────┘
              └──────────┬─────────┘
                         ▼
                  ┌─────────────┐
                  │    WRITER   │
                  │   Agent 08  │──── 3 formats in parallel
                  └──────┬──────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌──────────────┐
   │ EXECUTIVE  │ │  STANDARD  │ │  TECHNICAL   │
   │  700-900w  │ │ 3500-4500w │ │   Appendix   │
   │ 5 sections │ │ 8 sections │ │ Raw findings │
   └────────────┘ └────────────┘ └──────────────┘
```

---

## Agents

| # | Agent | Role | Key behaviour |
|---|-------|------|---------------|
| 01 | **Orchestrator** | Master controller | Retry queue, global state, loop orchestration |
| 02 | **Researcher** | Web intelligence | 3+ search angles, source scoring |
| 03 | **Classifier** | Domain taxonomy | 8-domain map, gap detection, follow-up loops |
| 04 | **Analyst** | Insight extraction | Relationship graphs, confidence scoring |
| 05 | **Devil's Advocate** | Adversarial critic | Counterarguments, fallacy detection, revision trigger |
| 06 | **Synthesizer** | Cross-domain synthesis | Non-obvious connections, headline finding |
| 07 | **Visualizer** | Content architecture | Section planning, executive summary |
| 08 | **Writer** | Report generation | 3 formats simultaneously, citation formatting |

---

## Features

<details>
<summary><strong>Adversarial critique loop</strong></summary>

Devil's Advocate scores every claim: **strong / moderate / weak / unverified**. If weak claims exceed 30% of total, it fires a revision request back to the Analyst. Runs up to 2 iterations before proceeding.
</details>

<details>
<summary><strong>Research gap filling</strong></summary>

After initial classification, ARIA checks which domains have fewer than 2 findings and sends targeted follow-up queries back to the Researcher. Maximum 2 gap-fill loops to prevent runaway calls.
</details>

<details>
<summary><strong>Cross-domain synthesis</strong></summary>

The Synthesizer is specifically tasked with finding connections *across* domains — the kind of insight that only appears when you hold economic, ethical, technical, and political findings simultaneously.
</details>

<details>
<summary><strong>Parallel report generation</strong></summary>

All three report formats are generated at the same time using `asyncio.gather`. Writer time is cut by ~60% compared to sequential generation.
</details>

<details>
<summary><strong>Live pipeline status via SSE</strong></summary>

The frontend connects over Server-Sent Events and watches each agent activate in real time. No polling. Each phase transition is pushed the moment it happens.
</details>

<details>
<summary><strong>Groq rate-limit resilience</strong></summary>

On a daily token-per-day (TPD) limit hit, ARIA automatically falls back from `llama-3.3-70b-versatile` to `llama-3.1-8b-instant` and retries — no error surfaced to the user.
</details>

<details>
<summary><strong>Query-level caching</strong></summary>

Identical queries within 24 hours return cached findings immediately, skipping the entire research phase. LLM responses are also individually cached with a configurable TTL.
</details>

---

## Report Formats

### Executive Briefing — 700–900 words
Intelligence-analyst style. Five structured sections:
1. Situation Assessment
2. Key Intelligence Findings
3. Risk Factors & Countervailing Forces
4. Strategic Implications
5. Bottom Line

### Standard Report — 3,500–4,500 words
Eight fully developed sections, each domain gets its own `###` subsection:
1. Executive Overview
2. Background & Context
3. Methodology & Data Sources
4. Domain-by-Domain Analysis
5. Cross-Domain Synthesis
6. Contested Claims & Uncertainty Analysis
7. Forward Implications & Strategic Outlook
8. Conclusion

### Technical Appendix
Raw pipeline data: all findings with confidence scores and source URLs, full insight inventory, Devil's Advocate critiques with weakness scores, cross-domain connections, and pipeline confidence metrics.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | Groq — `llama-3.3-70b-versatile` + `llama-3.1-8b-instant` | Fastest inference available; free 100k TPD |
| API | FastAPI + Uvicorn | Async-native, SSE support, minimal overhead |
| DB | SQLite | Zero-config, fully portable, complete observability |
| Frontend | Vanilla HTML/CSS/JS | No build step, no framework, instant load |
| Concurrency | `asyncio` + `ThreadPoolExecutor` | Parallel report gen + parallel research phases |
| Hosting | Render | Free tier, auto-deploy from GitHub |

---

## Project Structure

```
aria/
├── main.py                   # FastAPI app, SSE stream, job queue
├── orchestrator.py           # Master controller — runs all 8 agents
├── agents/
│   ├── researcher.py         # Web search + confidence scoring
│   ├── classifier.py         # Domain taxonomy + gap detection
│   ├── analyst.py            # Insight extraction + relationship mapping
│   ├── devil.py              # Adversarial critique + revision trigger
│   ├── synthesizer.py        # Cross-domain synthesis
│   ├── visualizer.py         # Report structure planning
│   └── writer.py             # Parallel report generation (3 formats)
├── core/
│   ├── groq_client.py        # API wrapper — caching, retry, TPD fallback
│   ├── memory.py             # SQLite layer — sessions, logs, reports
│   ├── state.py              # ARIAState dataclass
│   └── config.py             # Models, limits, timeouts
├── frontend/
│   ├── index.html
│   ├── style.css             # Neon dark / glassmorphism
│   └── app.js                # SSE client, pipeline visualiser, markdown renderer
├── db/                       # Auto-created on first run
└── requirements.txt
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/dhruv-2712/aria.git && cd aria

# 2. Install
pip install -r requirements.txt

# 3. Add your Groq API key (free at console.groq.com)
echo "GROQ_API_KEY=your_key_here" > .env

# 4. Run
python -m uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/research` | Start a research job |
| `GET` | `/stream/{id}` | SSE stream of live status |
| `GET` | `/status/{id}` | Job status + metadata |
| `GET` | `/status/latest` | Status of the most recent job |
| `GET` | `/report/{id}` | Final report — all 3 formats |
| `GET` | `/logs/{id}` | Full agent execution logs |
| `GET` | `/health` | Active job count |

```bash
# Start
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Impact of quantum computing on cryptography"}'

# Watch live
curl -N http://localhost:8000/stream/<session_id>

# Collect
curl http://localhost:8000/report/<session_id>
```

---

## Database Schema

```sql
sessions      id · query · created_at · status
agent_logs    session_id · agent_name · input_json · output_json · duration_ms
reports       session_id · executive · standard · technical · citations_json
findings      session_id · content · source_url · confidence · domain
```

Every agent call is stored with full input/output JSON and millisecond timing. Complete pipeline observability with zero extra config.

---

## Requirements

```
groq
fastapi
uvicorn[standard]
python-dotenv
pydantic
```

No GPU. No Docker. Runs on any machine with Python 3.11+.

---

<div align="center">
  <sub>Built with the Groq API · Deployed on Render · MIT License</sub>
</div>
