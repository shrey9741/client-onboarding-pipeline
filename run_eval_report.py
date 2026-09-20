"""
run_eval_report.py
Week 4 checkpoint: runs each test question through the full pipeline
(retrieval -> LLM synthesis -> citations), then through deterministic
DetEval-style checks (grounding, citation validity, relevance), and
saves a per-customer reliability report.

Usage:
    python run_eval_report.py
"""

import json
import os

from dotenv import load_dotenv
load_dotenv()

from ingestion.embedder import load_index
from ingestion.assistant import answer_question
from ingestion.llm_client import LLMClient
from eval.deteval_checks import run_checks
from run_week3_checkpoint import QUESTIONS


def run_customer_eval(customer_id: str, questions, llm_client) -> dict:
    index, vectorizer, metadata = load_index(customer_id)

    results = []
    for q in questions:
        rag_result = answer_question(q, index, vectorizer, metadata, llm_client=llm_client)

        eval_result = run_checks(
            question=q,
            answer=rag_result["answer"],
            citations=rag_result["citations"],
            context_chunks=rag_result["context_chunks"],
            metadata=metadata,
        )
        eval_result["provider"] = rag_result["provider"]
        eval_result["citations"] = rag_result["citations"]
        results.append(eval_result)

    total = len(results)
    passed = sum(1 for r in results if r["overall_pass"])

    return {
        "customer_id": customer_id,
        "total_questions": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "results": results,
    }


def print_report(report: dict):
    print(f"\n===== {report['customer_id']} — {report['passed']}/{report['total_questions']} passed "
          f"({report['pass_rate'] * 100:.1f}%) =====")

    for r in report["results"]:
        status = "PASS" if r["overall_pass"] else "FAIL"
        print(f"\n[{status}] {r['question']}")
        print(f"  answer ({r['provider']}): {r['answer'][:120]}")
        for c in r["checks"]:
            mark = "ok" if c["passed"] else "X "
            print(f"    [{mark}] {c['check']}: {c['detail']}")


def run(output_dir: str = "output"):
    llm_client = LLMClient()
    active_providers = [name for name, _ in llm_client.providers]
    print(f"Active providers (in fallback order): {active_providers or ['mock only -- no API keys set']}")

    all_reports = {}
    for customer_id, questions in QUESTIONS.items():
        report = run_customer_eval(customer_id, questions, llm_client)
        print_report(report)
        all_reports[customer_id] = report

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "eval_report.json")
    with open(out_path, "w") as f:
        json.dump(all_reports, f, indent=2)
    print(f"\nSaved full eval report -> {out_path}")


if __name__ == "__main__":
    run()
