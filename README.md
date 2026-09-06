# Client Onboarding Pipeline

A config-driven tool that takes a **raw, messy folder of a client's data** (CSV, Excel, PDFs, plain text — whatever mix they hand you) and automatically:

1. Detects and parses every file by type
2. Profiles the data (row counts, null %, PDF density, table detection, etc.)
3. *(in progress)* Auto-selects a chunking/retrieval strategy per file based on that profile
4. *(planned)* Builds a RAG assistant over the data, wired through an LLM gateway
5. *(planned)* Runs an automated evaluation (via [DetEval](#)) to produce a pass/fail reliability report before handoff
6. *(planned)* Deploys the whole thing with one command (Docker)

## Why this project exists

Most RAG demos assume one clean data source. Real onboarding — the kind a Forward Deployed Engineer or data analyst actually does — starts with a folder of inconsistent exports: some CSVs with missing values, a PDF vendor contract, a stray markdown file of meeting notes. This pipeline is built to prove that a system can **adapt automatically to whatever a new client hands you**, rather than being hand-tuned per project.

The same pipeline run unmodified against two structurally different customer folders should:
- Parse every file correctly
- Produce a distinct profile for each (because their data looks nothing alike)
- Eventually produce a working, evaluated assistant for each

## Current status: Week 1 — Ingestion & Auto-Detection ✅

Implemented and tested against two sample customer folders:

| Customer | Data | What the profiler caught |
|---|---|---|
| `customer_a` | 2 CSVs (suppliers, tickets) + 1 text note | Missing `on_time_pct` value (20% null), missing `customer_name` in a ticket (33% null) |
| `customer_b` | 1 PDF (vendor agreement, 3 pages) + 1 markdown note | Page count, average text density per page, table detection |

Roadmap for what's next is in [Roadmap](#roadmap) below.

## Architecture

```
Raw customer folder (CSV / Excel / PDF / TXT / MD)
              │
              ▼
      ┌───────────────┐
      │   router.py    │   classifies each file by extension/type
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │  parsers.py    │   type-specific parsing:
      │                │     - tabular -> pandas DataFrame + schema
      │                │     - pdf     -> per-page text + table detection
      │                │     - text    -> raw content
      └───────┬───────┘
              ▼
      ┌───────────────┐
      │  profiler.py   │   computes stats per file:
      │                │     - tabular: row/col counts, dtypes, null %
      │                │     - pdf: page count, text density, tables
      │                │     - text: char/line counts
      └───────┬───────┘
              ▼
    output/<customer_id>_profile.json
              │
              ▼ (Week 2, not yet built)
      Auto-config: chunk size / strategy per file, based on profile
              │
              ▼ (Week 3, not yet built)
      Embed -> FAISS -> LLM Gateway -> RAG answers with citations
              │
              ▼ (Week 4, not yet built)
      DetEval reliability report per customer
              │
              ▼ (Week 5, not yet built)
      Docker: one command to build + deploy a new customer's assistant
```

## Project structure

```
client-onboarding-pipeline/
├── ingestion/
│   ├── __init__.py
│   ├── router.py       # classifies files by type
│   ├── parsers.py      # per-type parsing logic
│   └── profiler.py     # per-file statistics/profiling
├── samples/
│   ├── customer_a/     # CSV-heavy sample data
│   └── customer_b/     # PDF-heavy sample data
├── output/              # generated profile JSON reports (git-ignored contents, folder kept)
├── run_ingestion.py     # entry point: route -> parse -> profile -> save JSON
├── requirements.txt
└── README.md
```

## Setup

```bash
git clone https://github.com/<your-username>/client-onboarding-pipeline.git
cd client-onboarding-pipeline

# (recommended) virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
```

## Usage

Run the ingestion pipeline against any customer folder under `samples/`:

```bash
python run_ingestion.py samples/customer_a
python run_ingestion.py samples/customer_b
```

Each run prints:
- A routing summary (which files were classified as tabular/PDF/text)
- A per-file profile (row counts, null %, PDF density, etc.)

...and saves a JSON report to `output/<customer_id>_profile.json`.

To test with your own data, drop any mix of `.csv`, `.xlsx`, `.pdf`, `.txt`, or `.md` files into a new folder under `samples/` and point the script at it:

```bash
python run_ingestion.py samples/my_new_customer
```

## Roadmap

- [x] **Week 1** — File routing, type-specific parsing, per-file profiling
- [ ] **Week 2** — Auto-config: pick chunk size/strategy per file based on its profile (e.g. dense PDF → smaller overlapping chunks; tabular with high null % → flag for cleaning before embedding)
- [ ] **Week 3** — Embed into FAISS, wire retrieval + answer synthesis through an LLM gateway (provider fallback, cost tracking), with source citations on every answer
- [ ] **Week 4** — Automated evaluation loop (DetEval) run after each customer build, producing a pass/fail reliability report
- [ ] **Week 5** — Dockerize so a new customer's assistant can be built and deployed with one command; minimal UI (upload → build → chat → eval report)
- [ ] **Week 6** — Polish: architecture write-up, tradeoff notes, demo deployment on public sample data

## Tech stack

- **Parsing:** pandas, openpyxl, pdfplumber
- **Planned:** FAISS (vector search), an LLM gateway for provider routing/fallback, DetEval for deterministic evaluation, Docker for deployment

## License

MIT
