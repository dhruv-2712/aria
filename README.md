# Autonomous Research & Intelligence Architecture

**One query. Seven agents. A publication-quality report in ~90 seconds.**

[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.1_8B_+_70B-f55036?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Render-6c63ff?style=flat-square&logo=render&logoColor=white)](https://aria-emh3.onrender.com)

**[→ Try the live demo](https://aria-emh3.onrender.com)**
*Free tier — may take ~15s to wake from sleep*

---

## What is ARIA?

ARIA is a multi-agent research pipeline that takes a question and autonomously produces an exhaustive intelligence report. It searches the live web, classifies findings across domains, extracts structured insights, stress-tests every claim with a Devil's Advocate, synthesizes cross-domain connections, and writes three distinct report formats — all without any manual steps.

No prompt engineering. No manual steps. One input → complete research output in ~90 seconds.

---

## Pipeline

```
                         ┌─────────────────────────────────┐
                         │            ORCHESTRATOR          │
                         │     retry logic · state mgmt    │
                         └──────────────┬──────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │    RESEARCHER    │
                              │  3 parallel web  │
                              │  searches · dedup│
                              └────────┬─────────┘
                                       │ findings
                                       ▼
                              ┌──────────────────┐
                              │   CLASSIFIER     │
                              │  8-domain map    │
                              └────────┬─────────┘
                                       │ domains
                                       ▼
                              ┌──────────────────┐
                              │     ANALYST      │
                              │ insights +       │
                              │ relationships    │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  DEVIL'S ADVOCATE│
                              │ 3 parallel calls │
                              │ critique·gaps·   │
                              │ fallacies        │
                              └────────┬─────────┘
                                       │
                          ┌────────────┴────────────┐ (parallel)
                          ▼                         ▼
               ┌──────────────────┐     ┌──────────────────┐
               │   SYNTHESIZER    │     │    VISUALIZER    │
               │ headline·narrative│     │ sections·summary │
               │ connections·     │     │                  │
               │ implications     │     │                  │
               └────────┬─────────┘     └────────┬─────────┘
                        └──────────┬─────────────┘
                                   ▼
                          ┌──────────────────┐
                          │      WRITER      │
                          │  executive (70B) │
                          │  + technical     │
                          └────────┬─────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌──────────┐  ┌──────────┐  ┌────────────┐
             │EXECUTIVE │  │FULL REPORT│  │ TECHNICAL  │
             │ 700-900w │  │3500-4500w │  │  Appendix  │
             │ streams  │  │ on demand │  │ raw data   │
             └──────────┘  └──────────┘  └────────────┘
```

---

## Agents

| # | Agent | Role | LLM calls |
|---|-------|------|-----------|
| 01 | **Orchestrator** | Master controller — retry logic, state, parallel execution | — |
| 02 | **Researcher** | 3 parallel web searches via Tavily/DuckDuckGo, URL dedup, content extraction | 1 (8B) |
| 03 | **Classifier** | Maps findings to 8 knowledge domains | 1 (8B) |
| 04 | **Analyst** | Extracts insights + relationship graph in a single merged call | 1 (8B) |
| 05 | **Devil's Advocate** | Critiques, finds missing perspectives, detects fallacies — all 3 in parallel | 3 parallel (8B) |
| 06 | **Synthesizer** | Headline finding, narrative arc, cross-domain connections, implications — single merged call | 1 (8B) |
| 07 | **Visualizer** | Plans report structure + executive summary (parallel with Synthesizer) | 2 (8B) |
| 08 | **Writer** | Streams the executive report live; generates full + technical on demand | 1 streaming (70B) |

**Total critical-path LLM calls: 7** — all 8B except the final writer (70B for quality).

---

## Features

<details>
<summary><strong>Live streaming executive report</strong></summary>

The executive briefing streams token-by-token as the Writer generates it — you see the report appear in real time before the pipeline fully completes.
</details>

<details>
<summary><strong>Lazy full report generation</strong></summary>

The 3,500–4,500 word standard report is generated on demand when you click the Full Report tab, keeping the initial pipeline fast. It also streams live as it's written.
</details>

<details>
<summary><strong>Adversarial critique</strong></summary>

Devil's Advocate runs three independent checks in parallel: counterarguments for every claim, missing stakeholder perspectives, and logical fallacy detection. Results feed directly into the Synthesizer and Writer.
</details>

<details>
<summary><strong>Cross-domain synthesis</strong></summary>

The Synthesizer is specifically tasked with finding connections *across* domains — the kind of insight that only appears when you hold economic, ethical, technical, and political findings simultaneously.
</details>

<details>
<summary><strong>Shareable reports</strong></summary>

Every completed report gets a permanent share link (`/r/{session_id}`) with full OG meta tags for rich link previews. The share page renders all three report tabs.
</details>

<details>
<summary><strong>Follow-up suggestions</strong></summary>

After each pipeline run, ARIA generates 3 suggested follow-up questions. Click any to immediately start a new research job pre-filled with that query.
</details>

<details>
<summary><strong>Session history</strong></summary>

All past sessions are stored and accessible via the History panel. Completed reports persist in the database and reload instantly.
</details>

<details>
<summary><strong>Export options</strong></summary>

Download any report tab as Markdown, print/save as PDF, or copy the full text to clipboard — all from the report toolbar.
</details>

<details>
<summary><strong>Rate limiting & job cap</strong></summary>

5 research requests per IP per hour via `slowapi`. Maximum 3 concurrent jobs server-wide to prevent resource exhaustion.
</details>

<details>
<summary><strong>Groq TPM resilience</strong></summary>

On a rate-limit or daily quota hit, ARIA automatically falls back from 70B to 8B and retries — no error surfaced to the user. The 8B model handles 131k tokens/minute vs 6k for 70B, making it the default for all intermediate agents.
</details>

---

## Report Formats

### Executive Briefing — 700–900 words — streams live
Intelligence-analyst style. Five structured sections:
1. Situation Assessment
2. Key Intelligence Findings
3. Risk Factors & Countervailing Forces
4. Strategic Implications
5. Bottom Line

### Standard Report — 3,500–4,500 words — generated on demand
Eight fully developed sections with domain-specific subsections:
1. Executive Overview · 2. Background & Context · 3. Methodology
4. Domain-by-Domain Analysis · 5. Cross-Domain Synthesis
6. Contested Claims · 7. Forward Implications · 8. Conclusion

### Technical Appendix
Raw pipeline data: all findings with confidence scores + source URLs, full insight inventory, Devil's Advocate critiques, cross-domain connections, pipeline confidence metrics.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM inference | Groq — `llama-3.1-8b-instant` + `llama-3.3-70b-versatile` | Fastest inference; 8B for speed, 70B for final report quality |
| Search | Tavily API (primary) + DuckDuckGo (fallback) | Real-time web data with content extraction |
| API | FastAPI + Uvicorn | Async-native, SSE support, minimal overhead |
| Streaming | Server-Sent Events | Token-by-token live streaming for both report types |
| DB | SQLite (local) / PostgreSQL (production) | Auto-detected via `DATABASE_URL` env var |
| Frontend | Vanilla HTML/CSS/JS | No build step, no framework, instant load |
| Concurrency | `asyncio` + `ThreadPoolExecutor` | Parallel agent execution + parallel web searches |
| Rate limiting | `slowapi` | 5 req/hour per IP, 3 concurrent jobs max |
| Hosting | Render | Auto-deploy from GitHub |

---

## Project Structure

```
aria/
├── main.py                   # FastAPI app, SSE streams, job queue, share pages
├── orchestrator.py           # Master controller — 7-agent pipeline
├── agents/
│   ├── researcher.py         # Parallel web search, content extraction
│   ├── classifier.py         # 8-domain classification
│   ├── analyst.py            # Merged insights + relationship extraction
│   ├── devil.py              # Parallel adversarial critique
│   ├── synthesizer.py        # Merged synthesis (headline, narrative, connections)
│   ├── visualizer.py         # Report structure planning
│   └── writer.py             # Streaming report generation (3 formats)
├── core/
│   ├── groq_client.py        # Groq wrapper — caching, retry, TPM fallback
│   ├── memory.py             # SQLite/PostgreSQL — sessions, logs, reports
│   ├── search.py             # Tavily + DuckDuckGo search layer
│   ├── dedup.py              # Near-duplicate finding removal
│   ├── state.py              # ARIAState dataclass
│   └── config.py             # Models, loop limits, timeouts
├── frontend/
│   ├── index.html            # Main app shell
│   ├── style.css             # Neon dark / glassmorphism UI
│   └── app.js                # SSE client, streaming renderer, history
└── requirements.txt
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/dhruv-2712/aria.git && cd aria

# 2. Install
pip install -r requirements.txt

# 3. Configure
echo "GROQ_API_KEY=your_key_here" > .env
# Optional: TAVILY_API_KEY=your_key (enables richer search results)

# 4. Run
python -m uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key — free at [console.groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | Recommended | Tavily search key — richer results than DDG fallback |
| `DATABASE_URL` | Production | PostgreSQL URL — falls back to SQLite if unset |
| `WEBHOOK_URL` | Optional | POST notification when a report completes |

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/research` | Start a research job (rate limited: 5/hour) |
| `GET` | `/stream/{id}` | SSE — live pipeline status |
| `GET` | `/stream-report/{id}` | SSE — executive report token stream |
| `GET` | `/stream-standard-report/{id}` | SSE — full report token stream |
| `POST` | `/generate-standard/{id}` | Trigger lazy full report generation |
| `GET` | `/status/{id}` | Job status, metadata, error |
| `GET` | `/report/{id}` | Final report — all formats + follow-ups |
| `GET` | `/r/{id}` | Shareable report page (HTML) |
| `GET` | `/sessions` | 20 most recent completed sessions |
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
sessions    id · query · created_at · status
agent_logs  session_id · agent_name · input_json · output_json · duration_ms
reports     session_id · executive · standard · technical · citations_json · follow_ups_json
```

Every agent call is stored with full input/output JSON and millisecond timing.

---

<div align="center">
  <sub>Built with the Groq API · Tavily Search · Deployed on Render · MIT License</sub>
</div>
