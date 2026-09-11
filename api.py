"""
api.py
Week 3: FastAPI endpoint wrapping the assistant.

Run:
    uvicorn api:app --reload

Then:
    POST /customers/customer_a/query   {"question": "..."}
    GET  /health
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ingestion.embedder import load_index
from ingestion.assistant import answer_question
from ingestion.llm_client import LLMClient

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Client Onboarding Pipeline API")

# one shared client so provider fallback + usage log persist across requests
llm_client = LLMClient()


class QueryRequest(BaseModel):
    question: str


@app.post("/customers/{customer_id}/query")
def query_customer(customer_id: str, req: QueryRequest):
    try:
        index, vectorizer, metadata = load_index(customer_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No index found for customer '{customer_id}'. Run run_indexing.py first.",
        )

    result = answer_question(req.question, index, vectorizer, metadata, llm_client=llm_client)
    # context_chunks is internal (used by the eval pipeline) -- don't expose full
    # retrieved text on every API response, citations are enough for the client.
    result.pop("context_chunks", None)
    return result


@app.get("/health")
def health():
    return {"status": "ok"}
