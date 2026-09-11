# 📥 Client Onboarding Pipeline — Auto-Adapting RAG Builder

> Point it at any client's messy data dump. It figures out the rest.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Profiling-150458?style=flat-square&logo=pandas&logoColor=white)
![pdfplumber](https://img.shields.io/badge/pdfplumber-PDF%20Parsing-8A2BE2?style=flat-square)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-4B8BBE?style=flat-square)
![DetEval](https://img.shields.io/badge/DetEval-Reliability%20Report-2E8B57?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Deploy-2496ED?style=flat-square&logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/Status-Week%202%20Complete-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)

---

## 📌 The Problem

Every new client hands you data in a different shape — a few messy CSVs, a PDF contract, a stray markdown file of meeting notes, always with missing values and inconsistent formatting. Most RAG demos assume one clean source. Real onboarding doesn't work that way, and hand-tuning a pipeline per client doesn't scale.

## 💡 The Solution

This pipeline takes a **raw, unstructured client folder** and automatically:

1. **Detects & parses** every file by type (CSV/Excel → pandas, PDF → pdfplumber, text → raw)
2. **Profiles** the data — row counts, null %, PDF text density, table detection
3. **Auto-configures** a chunking/retrieval strategy per file based on that profile *(Week 2)*
4. **Builds a RAG assistant** over the data with source citations on every answer *(Week 3)*
5. **Runs an automated eval** via DetEval to produce a pass/fail reliability report before handoff *(Week 4)*
6. **Deploys with one command** via Docker *(Week 5)*

The same pipeline, run unmodified on two structurally different client folders, should parse both correctly and produce a distinct, accurate profile for each — proving it adapts rather than being hand-tuned.

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
   output/<customer_id>_profile.json
              │
              ▼  Week 2 →  Week 3 →   Week 4    →  Week 5
        auto-config    RAG + LLM   DetEval report   Docker
        per file       gateway    (pass/fail)       one-command deploy
```

---

## ✅ Current Status — Week 2: Auto-Config, Chunking & Vector Index

| Customer | Data | Auto-config decision |
|---|---|---|
| `customer_a` | `suppliers.csv` | row-level chunking; **flagged for cleaning** (20% null in `on_time_pct`) |
| `customer_a` | `tickets.csv` | row-level chunking; **flagged for cleaning** (33% null in `customer_name`) |
| `customer_b` | `vendor_agreement.pdf` | sparse text → chunk_size=1000/overlap=150 (would be 500/100 if dense) |

Each customer's chunks are embedded (TF-IDF) and indexed into a per-customer FAISS index. A sanity search confirms it retrieves correctly, e.g. `"delay"` surfaces the two worst-performing suppliers by `avg_delay_days`; `"penalty"` surfaces the exact contract clause in the PDF.

> **Embedding note:** uses TF-IDF (scikit-learn) rather than a downloaded neural embedding model — dependency-light, fully offline, easy to swap for `sentence-transformers` later without touching the FAISS/retrieval layer.

## 🗺️ Roadmap

- [x] **Week 1** — File routing, type-specific parsing, per-file profiling
- [x] **Week 2** — Auto-config per file (chunk size/strategy, cleaning flags), chunking, TF-IDF + FAISS indexing
- [x] **Week 3** — LLM gateway client (Groq/OpenAI/Anthropic fallback), RAG answer synthesis with citations, FastAPI endpoint
- [x] **Week 4** — Deterministic reliability checks (grounding, citation validity, relevance) + per-customer eval report
- [ ] **Week 5** — Docker one-command deploy + minimal UI
- [ ] **Week 6** — Architecture write-up, tradeoffs, live demo on public data

---

## ⚙️ Setup

```bash
git clone https://github.com/<your-username>/client-onboarding-pipeline.git
cd client-onboarding-pipeline

python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
```

## ▶️ Usage

**Week 1 — routing, parsing, profiling only:**
```bash
python run_ingestion.py samples/customer_a
python run_ingestion.py samples/customer_b
```
Prints a routing summary + per-file profile, and saves a JSON report to `output/<customer_id>_profile.json`.

**Week 2 — full pipeline through a searchable index:**
```bash
python run_indexing.py samples/customer_a
python run_indexing.py samples/customer_b
```
Runs routing → parsing → profiling → auto-config → chunking → embedding, and builds a FAISS index per customer. Also runs a quick sanity search against the freshly built index so you can see retrieval working end to end. Saves:
- `output/<customer_id>_config.json` — auto-config decisions + reasons per file
- `output/<customer_id>/index.faiss`, `vectorizer.pkl`, `metadata.json` — the searchable index

Drop your own mix of `.csv`, `.xlsx`, `.pdf`, `.txt`, or `.md` into a new folder under `samples/` and point either script at it to test with real data.

## 📂 Project Structure

```
client-onboarding-pipeline/
├── ingestion/
│   ├── router.py        # file-type classification
│   ├── parsers.py       # per-type parsing
│   ├── profiler.py      # per-file statistics
│   ├── auto_config.py   # picks chunk strategy/size per file from its profile
│   ├── chunker.py       # implements each chunking strategy
│   └── embedder.py      # TF-IDF embedding + FAISS index build/search
├── samples/
│   ├── customer_a/      # CSV-heavy sample
│   └── customer_b/      # PDF-heavy sample
├── output/               # profile/config JSON + per-customer FAISS indexes
├── run_ingestion.py      # Week 1 entry point
├── run_indexing.py       # Week 2 entry point
├── requirements.txt
└── README.md
```

---

## 📄 License

MIT
