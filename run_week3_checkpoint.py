"""
run_week3_checkpoint.py
Runs 10 questions per customer through: retrieval -> LLM synthesis -> citations.

Usage:
    python run_week3_checkpoint.py

Set GROQ_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY in your environment
to use a real provider. With none set, runs in mock mode so the full
pipeline is still testable offline.
"""

from ingestion.embedder import load_index
from ingestion.assistant import answer_question
from ingestion.llm_client import LLMClient

from dotenv import load_dotenv
load_dotenv()

QUESTIONS = {
    "customer_a": [
        "Which supplier has the worst on-time delivery percentage?",
        "What is the average delay for Bharat Freight?",
        "Which region has the most delayed suppliers?",
        "Is there a supplier with missing on-time data?",
        "What ticket involves a wrong item being shipped?",
        "Which open ticket is about a late delivery?",
        "What did the Q3 ops notes say to focus on?",
        "Which supplier is in the West region?",
        "What issue did Priya Singh report?",
        "How many tickets are currently open?",
    ],
    "customer_b": [
        "What on-time delivery rate must vendors maintain?",
        "What happens if a vendor misses the SLA for two quarters?",
        "What is the penalty for a shipment more than 5 days late?",
        "How soon must damaged goods be reported after receipt?",
        "What are the meeting notes about?",
        "Which two parties are named in the vendor agreement?",
        "What section covers penalty clauses?",
        "What section covers service level expectations?",
        "Is the penalty applied per shipment or per invoice?",
        "By when should SLA terms be renegotiated?",
    ],
}


def run_checkpoint():
    llm_client = LLMClient()
    active_providers = [name for name, _ in llm_client.providers]
    print(f"Active providers (in fallback order): {active_providers or ['mock only -- no API keys set']}")

    for customer_id, questions in QUESTIONS.items():
        print(f"\n===== {customer_id} =====")
        index, vectorizer, metadata = load_index(customer_id)

        for i, q in enumerate(questions, 1):
            result = answer_question(q, index, vectorizer, metadata, llm_client=llm_client)
            print(f"\n[{i}] Q: {q}")
            print(f"    A ({result['provider']}): {result['answer'][:180]}")
            for c in result["citations"]:
                print(f"    cite: {c['source_file']} | {c['locator']}")


if __name__ == "__main__":
    run_checkpoint()
