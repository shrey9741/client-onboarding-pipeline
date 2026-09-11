"""
deteval_checks.py
Week 4: deterministic, rule-based reliability checks -- same philosophy
as the DetEval project (no LLM-as-judge): every check here is a plain
numeric/rule computation, fully reproducible and explainable.

NOTE: this is a dependency-light stand-in for the real DetEval package,
which uses NLI entailment + sentence-transformers semantic similarity
for stronger grounding checks. The grounding check here uses TF-IDF
cosine similarity instead -- weaker than true semantic similarity, but
deterministic, offline, and needs no model downloads. Swap in the real
DetEval scorer at `grounding_check()` if you want the stronger version;
everything else (citation validity, relevance, report aggregation)
stays the same.
"""

from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

GROUNDING_THRESHOLD = 0.15
RELEVANCE_THRESHOLD = 0.05


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    if not text_a.strip() or not text_b.strip():
        return 0.0
    vectorizer = TfidfVectorizer(token_pattern=r"(?u)[A-Za-z]+")
    try:
        matrix = vectorizer.fit_transform([text_a, text_b])
    except ValueError:
        # happens if both texts share zero vocabulary after tokenizing
        return 0.0
    return float(cosine_similarity(matrix[0], matrix[1])[0][0])


def grounding_check(answer: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Flags potential hallucination: does the answer's wording actually
    overlap with the retrieved context, or does it look unrelated to
    everything that was retrieved?
    """
    context_text = " ".join(c["text"] for c in context_chunks)
    score = _tfidf_similarity(answer, context_text)
    passed = score >= GROUNDING_THRESHOLD

    return {
        "check": "grounding",
        "passed": passed,
        "score": round(score, 3),
        "threshold": GROUNDING_THRESHOLD,
        "detail": (
            f"answer/context TF-IDF similarity {score:.3f} "
            f"({'>=' if passed else '<'} threshold {GROUNDING_THRESHOLD})"
        ),
    }


def citation_validity_check(citations: List[Dict[str, Any]], metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Confirms every cited (source_file, locator) pair actually exists in
    the index metadata -- catches a citation that was fabricated or
    detached from the real retrieved chunk.
    """
    valid_pairs = {(m["source_file"], m["locator"]) for m in metadata}
    invalid = [
        c for c in citations
        if (c["source_file"], c["locator"]) not in valid_pairs
    ]
    passed = len(invalid) == 0

    return {
        "check": "citation_validity",
        "passed": passed,
        "invalid_citations": invalid,
        "detail": (
            "all citations match indexed chunks"
            if passed
            else f"{len(invalid)} citation(s) do not match any indexed chunk"
        ),
    }


def relevance_check(question: str, answer: str) -> Dict[str, Any]:
    """
    Confirms the answer engages with the question at all -- catches
    empty, generic, or completely off-topic responses.
    """
    score = _tfidf_similarity(question, answer)
    passed = score >= RELEVANCE_THRESHOLD

    return {
        "check": "relevance",
        "passed": passed,
        "score": round(score, 3),
        "threshold": RELEVANCE_THRESHOLD,
        "detail": (
            f"question/answer TF-IDF similarity {score:.3f} "
            f"({'>=' if passed else '<'} threshold {RELEVANCE_THRESHOLD})"
        ),
    }


def run_checks(question: str, answer: str, citations: List[Dict[str, Any]],
                context_chunks: List[Dict[str, Any]], metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
    checks = [
        grounding_check(answer, context_chunks),
        citation_validity_check(citations, metadata),
        relevance_check(question, answer),
    ]

    all_passed = all(c["passed"] for c in checks)

    return {
        "question": question,
        "answer": answer,
        "checks": checks,
        "overall_pass": all_passed,
    }
