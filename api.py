"""
api.py
Week 5 (revised): the real API surface a frontend wires to. Every endpoint
returns real data from the actual pipeline -- no mocked stats, no fake
throughput/telemetry numbers.

Run:
    uvicorn api:app --reload

Endpoints:
    POST /customers/{id}/build          upload files, run the pipeline (background)
    GET  /customers                     list clients that have a built index
    GET  /customers/{id}/status         live per-stage pipeline status
    GET  /customers/{id}/profile        raw per-file profiling stats
    GET  /customers/{id}/config         auto-config decisions per file
    POST /customers/{id}/query          ask a question, get an answer + citations
    POST /customers/{id}/eval           ask a question, get eval checks (grounding/citation/relevance)
    GET  /health
"""

import os
import json
import shutil
import threading
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

from onboard import onboard_client, STAGE_ORDER
from ingestion.embedder import load_index
from ingestion.assistant import answer_question
from ingestion.llm_client import LLMClient
from eval.deteval_checks import run_checks

app = FastAPI(title="Client Onboarding Pipeline API")

# Allows a separately-hosted frontend (e.g. a Stitch-exported React app running
# on a different port/origin) to call this API directly from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_client = LLMClient()

OUTPUT_DIR = "output"
UPLOAD_DIR = "uploaded_clients"

# In-memory pipeline state, keyed by customer_id. Fine for a single-process
# internal tool; would move to Redis/DB if this ever needed multi-worker deploy.
_state_lock = threading.Lock()
PIPELINE_STATE = {}


def _init_state(customer_id: str):
    with _state_lock:
        PIPELINE_STATE[customer_id] = {
            "customer_id": customer_id,
            "overall": "running",
            "error": None,
            "stages": {s: "pending" for s in STAGE_ORDER},
            "detail": {},
        }


def _update_state(customer_id: str, stage_key: str, status: str, detail: Optional[str] = None):
    with _state_lock:
        state = PIPELINE_STATE.get(customer_id)
        if state is None:
            return
        if stage_key == "done":
            state["overall"] = "done"
            return
        state["stages"][stage_key] = status
        if detail:
            state["detail"][stage_key] = detail


def _run_pipeline_background(customer_id: str, folder_path: str):
    def on_stage(stage_key, status, detail=None):
        _update_state(customer_id, stage_key, status, detail)

    try:
        onboard_client(folder_path, output_dir=OUTPUT_DIR, on_stage=on_stage)
    except Exception as e:
        with _state_lock:
            state = PIPELINE_STATE.get(customer_id)
            if state is not None:
                state["overall"] = "error"
                state["error"] = str(e)


def _list_built_customers() -> List[str]:
    clients = []
    if os.path.isdir(OUTPUT_DIR):
        for name in os.listdir(OUTPUT_DIR):
            full = os.path.join(OUTPUT_DIR, name)
            if os.path.isdir(full) and os.path.isfile(os.path.join(full, "index.faiss")):
                clients.append(name)
    return sorted(clients)


def _load_json(path: str):
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


# ------------------------------------------------------------------- build
@app.post("/customers/{customer_id}/build")
async def build_customer(customer_id: str, background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    client_folder = os.path.join(UPLOAD_DIR, customer_id)
    os.makedirs(client_folder, exist_ok=True)

    for uf in files:
        dest_path = os.path.join(client_folder, uf.filename)
        with open(dest_path, "wb") as out:
            shutil.copyfileobj(uf.file, out)

    _init_state(customer_id)
    background_tasks.add_task(_run_pipeline_background, customer_id, client_folder)

    return {"customer_id": customer_id, "status": "started", "file_count": len(files)}


# ------------------------------------------------------------------ status
@app.get("/customers/{customer_id}/status")
def get_status(customer_id: str):
    state = PIPELINE_STATE.get(customer_id)

    if state is None:
        # not currently tracked in-memory (e.g. server restarted) -- fall back
        # to whether a finished index exists on disk
        if customer_id in _list_built_customers():
            config = _load_json(os.path.join(OUTPUT_DIR, f"{customer_id}_config.json"))
            return {
                "customer_id": customer_id,
                "overall": "done",
                "error": None,
                "stages": {s: "done" for s in STAGE_ORDER},
                "detail": {},
                "flagged_for_cleaning": config["flagged_for_cleaning"] if config else [],
            }
        raise HTTPException(status_code=404, detail=f"No build found for customer '{customer_id}'.")

    result = dict(state)
    if state["overall"] == "done":
        config = _load_json(os.path.join(OUTPUT_DIR, f"{customer_id}_config.json"))
        result["flagged_for_cleaning"] = config["flagged_for_cleaning"] if config else []

    return result


# ----------------------------------------------------------------- listing
@app.get("/customers")
def list_customers():
    return {"customers": _list_built_customers()}


# ----------------------------------------------------------------- profile
@app.get("/customers/{customer_id}/profile")
def get_profile(customer_id: str):
    profile = _load_json(os.path.join(OUTPUT_DIR, f"{customer_id}_profile.json"))
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No profile found for customer '{customer_id}'.")
    return profile


# ------------------------------------------------------------------ config
@app.get("/customers/{customer_id}/config")
def get_config(customer_id: str):
    config = _load_json(os.path.join(OUTPUT_DIR, f"{customer_id}_config.json"))
    if config is None:
        raise HTTPException(status_code=404, detail=f"No config found for customer '{customer_id}'.")
    return config


# ------------------------------------------------------------------- query
class QueryRequest(BaseModel):
    question: str


@app.post("/customers/{customer_id}/query")
def query_customer(customer_id: str, req: QueryRequest):
    try:
        index, vectorizer, metadata = load_index(customer_id, output_dir=OUTPUT_DIR)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No index found for customer '{customer_id}'. Build it first.",
        )

    result = answer_question(req.question, index, vectorizer, metadata, llm_client=llm_client)
    result.pop("context_chunks", None)  # internal only, not part of the API contract
    return result


# -------------------------------------------------------------------- eval
class EvalRequest(BaseModel):
    question: str


@app.post("/customers/{customer_id}/eval")
def eval_customer(customer_id: str, req: EvalRequest):
    try:
        index, vectorizer, metadata = load_index(customer_id, output_dir=OUTPUT_DIR)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No index found for customer '{customer_id}'. Build it first.",
        )

    rag_result = answer_question(req.question, index, vectorizer, metadata, llm_client=llm_client)
    eval_result = run_checks(
        question=req.question,
        answer=rag_result["answer"],
        citations=rag_result["citations"],
        context_chunks=rag_result["context_chunks"],
        metadata=metadata,
    )
    eval_result["provider"] = rag_result["provider"]
    return eval_result


@app.get("/health")
def health():
    return {"status": "ok"}