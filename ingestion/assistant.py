"""
assistant.py
Week 3: ties retrieval (Week 2's FAISS index) to LLM answer synthesis,
producing a grounded answer with source citations for every response.
"""

from ingestion.embedder import search
from ingestion.llm_client import LLMClient

PROMPT_TEMPLATE = """You are a client onboarding assistant. Answer the question using ONLY the context below. If the answer isn't in the context, say so plainly. Be concise.

Context:
{context}

Question: {question}

Answer:"""


def build_prompt(question, chunks):
    context = "\n\n".join(
        f"[{i + 1}] (source: {c['source_file']} | {c['locator']})\n{c['text']}"
        for i, c in enumerate(chunks)
    )
    return PROMPT_TEMPLATE.format(context=context, question=question)


def answer_question(question, index, vectorizer, metadata, llm_client=None, top_k=3):
    chunks = search(question, index, vectorizer, metadata, top_k=top_k)

    if llm_client is None:
        llm_client = LLMClient()

    if not chunks:
        return {
            "question": question,
            "answer": "No relevant information was found in the client's data for this question.",
            "citations": [],
            "provider": "none",
        }

    prompt = build_prompt(question, chunks)
    answer_text, provider = llm_client.generate(prompt, context_chunks=chunks)

    citations = [
        {"source_file": c["source_file"], "locator": c["locator"]} for c in chunks
    ]

    return {
        "question": question,
        "answer": answer_text,
        "citations": citations,
        "context_chunks": chunks,
        "provider": provider,
    }
