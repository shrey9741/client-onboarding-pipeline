# 📥 Client Onboarding Pipeline — Auto-Adapting RAG Builder

> Point it at any client's messy data dump. It figures out the rest.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-Vite%20%2B%20Tailwind-61DAFB?style=flat-square&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?style=flat-square&logo=fastapi&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Profiling-150458?style=flat-square&logo=pandas&logoColor=white)
![pdfplumber](https://img.shields.io/badge/pdfplumber-PDF%20Parsing-8A2BE2?style=flat-square)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-4B8BBE?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA%203.1-F55036?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Deploy-2496ED?style=flat-square&logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/Status-Week%206%20(Polish)-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)

**[🔗 Live demo](#) · Coming in Week 6**

---

## 📌 The Problem

Every new client hands you data in a different shape — a few messy CSVs, a PDF contract, a stray markdown file of meeting notes, always with missing values and inconsistent formatting. Most RAG demos assume one clean source. Real onboarding doesn't work that way, and hand-tuning a pipeline per client doesn't scale.

## 💡 The Solution

This pipeline takes a **raw, unstructured client folder** and automatically:

1. **Detects & parses** every file by type (CSV/Excel → pandas, PDF → pdfplumber, text → raw)
2. **Profiles** the data — row counts, null %, PDF text density, table detection
3. **Auto-configures** a chunking/retrieval strategy per file based on that profile
4. **Builds a RAG assistant** over the data with source citations on every answer
5. **Runs deterministic reliability checks** (grounding, citation validity, relevance) before handoff
6. **Deploys via Docker**, with a REST API any frontend can wire to — including the React dashboard shipped in this repo

The same pipeline, run unmodified on two structurally different client folders, parses both correctly and produces a distinct, accurate config/profile for each — proving it adapts rather than being hand-tuned per client.

---

## 🏗️ Architecture

```
Raw client folder (CSV / Excel / PDF / TXT / MD)
              │
              ▼
      ┌───────────────┐
      │   router.py    │  classifies each file by type
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │  parsers.py    │  tabular → DataFrame + schema
      │                │  pdf     → per-page text + tables
      │                │  text    → raw content
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │  profiler.py   │  row/col counts, null %, dtypes,
      │                │  PDF page density, table detection
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │ auto_config.py │  picks chunk strategy/size per file,
      │                │  flags data-quality issues
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │  chunker.py    │  row-level (tabular) or sliding-window
      │                │  (pdf/text) chunking
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │  embedder.py   │  TF-IDF vectors → FAISS index per client
      └───────┬───────┘
              ▼
      ┌───────────────┐      ┌──────────────────┐
      │  assistant.py  │◄────│  llm_client.py     │  Groq → OpenAI →
      │  retrieval +   │     │  provider fallback │  Anthropic → mock
      │  prompt + cite │     └──────────────────┘
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │deteval_checks.py│  grounding / citation validity /
      │                │  relevance — deterministic, no LLM-judge
      └───────┬───────┘
              ▼
      ┌───────────────┐      ┌──────────────────┐
      │    api.py      │◄────│  React dashboard   │  client-onboarding-ui/
      │  REST surface  │─────►  (build / config /  │  Vite + Tailwind
      └───────────────┘      │  profile / ask)    │
                              └──────────────────┘
```

---

## ✅ Current Status

All 6 pipeline stages are built and tested end-to-end (route → parse → profile → auto-config → chunk → embed/index), backed by a full REST API and a React frontend wired to real data — nothing in the UI is mocked.

| Customer | Data | Auto-config decision |
|---|---|---|
| `customer_a` | `suppliers.csv` | row-level chunking; **flagged for cleaning** (20% null in `on_time_pct`) |
| `customer_a` | `tickets.csv` | row-level chunking; **flagged for cleaning** (33% null in `customer_name`) |
| `customer_b` | `vendor_agreement.pdf` | sparse text → chunk_size=1000/overlap=150 (would be 500/100 if dense) |

A sanity search confirms retrieval works correctly, e.g. `"delay"` surfaces the two worst-performing suppliers by `avg_delay_days`; `"penalty"` surfaces the exact contract clause in the PDF. Every RAG answer ships with source citations (file + row/page), and every answer can be run through 3 deterministic reliability checks before you'd trust it in front of a client.

## 🧠 Design Decisions & Tradeoffs

- **TF-IDF instead of a neural embedding model.** Dependency-light, fully offline, no model downloads — good enough to prove retrieval works correctly (verified against 20 test questions across both sample clients). The FAISS layer is embedding-agnostic, so swapping in `sentence-transformers` later only touches `embedder.py`.
- **Deterministic eval checks instead of LLM-as-judge.** Grounding (TF-IDF similarity between answer and retrieved context), citation validity (do cited sources actually exist in the index), and relevance (does the answer engage with the question) are all plain, reproducible computations — no second LLM call, no judge-model bias, fully explainable in an interview.
- **Provider fallback + mock mode in the LLM client.** Tries Groq → OpenAI → Anthropic in order; if no API key is configured, falls back to a deterministic mock answer built from the retrieved context. This kept the retrieval → prompt → citation plumbing fully testable offline before ever spending API credits.
- **Auto-config is rule-based, not LLM-based.** Chunking decisions (row-level vs. sliding-window, chunk size, cleaning flags) come from simple, named thresholds on the profiling stats — deterministic and cheap, and the reasoning is directly inspectable (every decision ships with a plain-English `reason` string).

## 🗺️ Roadmap

- [x] **Week 1** — File routing, type-specific parsing, per-file profiling
- [x] **Week 2** — Auto-config per file (chunk size/strategy, cleaning flags), chunking, TF-IDF + FAISS indexing
- [x] **Week 3** — LLM gateway client (Groq/OpenAI/Anthropic fallback), RAG answer synthesis with citations, FastAPI endpoint
- [x] **Week 4** — Deterministic reliability checks (grounding, citation validity, relevance) + per-customer eval report
- [x] **Week 5** — Docker, one-command onboarding function, full REST API surface (build/status/profile/config/query/eval)
- [x] **Frontend** — React (Vite + Tailwind) dashboard: client directory, live build progress, Config/Profile/Ask tabs, wired entirely to real endpoints
- [ ] **Week 6** — Live deployment (backend + frontend), demo video, this README's final pass

---

## ⚙️ Setup (backend)

```bash
git clone https://github.com/<your-username>/client-onboarding-pipeline.git
cd client-onboarding-pipeline

python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
```

Add a `.env` file in the project root with at least one LLM provider key (optional — falls back to mock mode without one):
```
GROQ_API_KEY=your-key-here
```

## ▶️ Usage

**Full pipeline via CLI (one command):**
```bash
python onboard.py samples/customer_a
```
Runs routing → parsing → profiling → auto-config → chunking → embedding, with live structured progress output, and saves everything to `output/`.

**Run the API:**
```bash
uvicorn api:app --reload
```
Interactive docs at `http://localhost:8000/docs` — every endpoint (including file upload) is testable directly in the browser.

**Run the reliability checkpoint (10 questions × 2 sample clients):**
```bash
python run_eval_report.py
```
Saves `output/eval_report.json` with a pass/fail breakdown per question.

Drop your own mix of `.csv`, `.xlsx`, `.pdf`, `.txt`, or `.md` into a new folder under `samples/`, or upload through the React UI, to test with real data.

## 🖥️ Setup (frontend)

```bash
cd client-onboarding-ui
npm install
npm run dev
```
Runs at `http://localhost:5173`. Requires the backend (`uvicorn api:app --reload`) running at `http://localhost:8000` — the API base URL is editable directly in the UI header if yours differs.

## 🐳 Running with Docker

```bash
docker-compose up --build
```

API runs at `http://localhost:8000` (interactive docs at `/docs`). Reads your Groq/OpenAI/Anthropic key from `.env` in the project root (never baked into the image). `output/`, `samples/`, and `uploaded_clients/` are mounted as volumes so indexes persist across container restarts.

To build/run without compose:
```bash
docker build -t onboarding-api .
docker run -p 8000:8000 --env-file .env onboarding-api
```

## 🔌 API Reference

The React dashboard wires to these — every response is real pipeline data, nothing mocked:

| Method | Endpoint | Returns |
|---|---|---|
| `POST` | `/customers/{id}/build` | Upload files (multipart), starts the pipeline in the background |
| `GET` | `/customers/{id}/status` | Live per-stage status (`route`/`parse`/`profile`/`config`/`chunk`/`index`), each `pending`/`running`/`done`, plus a `detail` string per stage |
| `GET` | `/customers` | List of clients with a completed build |
| `GET` | `/customers/{id}/profile` | Raw per-file profiling stats (row counts, null %, PDF density) |
| `GET` | `/customers/{id}/config` | Auto-config decision + reason per file |
| `POST` | `/customers/{id}/query` | `{"question": "..."}` → grounded answer + citations |
| `POST` | `/customers/{id}/eval` | `{"question": "..."}` → grounding/citation/relevance check results |
| `GET` | `/health` | `{"status": "ok"}` |

## 📂 Project Structure

```
client-onboarding-pipeline/
├── ingestion/
│   ├── router.py         # file-type classification
│   ├── parsers.py        # per-type parsing
│   ├── profiler.py       # per-file statistics
│   ├── auto_config.py    # picks chunk strategy/size per file from its profile
│   ├── chunker.py        # implements each chunking strategy
│   ├── embedder.py       # TF-IDF embedding + FAISS index build/search
│   ├── llm_client.py     # gateway-style LLM client (provider fallback, mock mode)
│   └── assistant.py      # retrieval -> prompt -> LLM synthesis -> citations
├── eval/
│   └── deteval_checks.py   # deterministic grounding/citation/relevance checks
├── samples/
│   ├── customer_a/       # CSV-heavy sample
│   └── customer_b/       # PDF-heavy sample
├── output/                # profile/config JSON, FAISS indexes, eval reports
├── client-onboarding-ui/  # React (Vite + Tailwind) frontend
│   └── src/App.jsx         # client directory, build view, dashboard
├── onboard.py              # one-command pipeline entry point, structured stage events
├── api.py                  # FastAPI: build/status/profile/config/query/eval endpoints
├── run_ingestion.py         # Week 1 checkpoint
├── run_indexing.py          # Week 2 checkpoint
├── run_week3_checkpoint.py  # Week 3 checkpoint
├── run_eval_report.py       # Week 4 checkpoint
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 📄 License

MIT
