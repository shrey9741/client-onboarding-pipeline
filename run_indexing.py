"""
run_indexing.py
Week 2 checkpoint script.

Usage:
    python run_indexing.py samples/customer_a
    python run_indexing.py samples/customer_b

Runs: route -> parse -> profile -> auto_config -> chunk -> embed -> save index
Saves per customer:
    output/<customer_id>_profile.json   (from Week 1)
    output/<customer_id>_config.json    (auto-config decisions + reasons)
    output/<customer_id>/index.faiss
    output/<customer_id>/vectorizer.pkl
    output/<customer_id>/metadata.json
"""


import sys
import json
import os

from ingestion.router import route_folder, print_routing_summary
from ingestion.parsers import parse_file
from ingestion.profiler import profile_customer
from ingestion.auto_config import configure_customer
from ingestion.chunker import chunk_file
from ingestion.embedder import build_index, save_index, load_index, search


def run(folder_path: str, output_dir: str = "output"):
    routing = route_folder(folder_path)
    print_routing_summary(routing)

    parsed_files = []
    for f in routing.all_files():
        if f.kind == "unsupported":
            continue
        parsed_files.append(parse_file(f))

    profile = profile_customer(parsed_files)
    config_result = configure_customer(profile)

    print("\n--- Auto-Config Decisions ---")
    for cfg in config_result["configs"]:
        print(f"  {cfg['filename']}: {cfg['reason']}")
    if config_result["flagged_for_cleaning"]:
        print(f"\n  ⚠ Flagged for cleaning: {config_result['flagged_for_cleaning']}")

    # chunk every file using its matching config
    config_by_filename = {c["filename"]: c for c in config_result["configs"]}
    all_chunks = []
    for parsed in parsed_files:
        cfg = config_by_filename[parsed["filename"]]
        file_chunks = chunk_file(parsed, cfg)
        all_chunks.extend(file_chunks)
        print(f"  Chunked {parsed['filename']} -> {len(file_chunks)} chunk(s)")

    print(f"\nTotal chunks for {routing.customer_id}: {len(all_chunks)}")

    index, vectorizer, metadata = build_index(all_chunks)
    save_index(routing.customer_id, index, vectorizer, metadata, output_dir)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, f"{routing.customer_id}_config.json"), "w") as f:
        json.dump(config_result, f, indent=2)

    print(f"Saved FAISS index -> {output_dir}/{routing.customer_id}/")
    return routing.customer_id, all_chunks


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "samples/customer_a"
    customer_id, chunks = run(folder)

    # quick sanity-check search against the freshly built index
    index, vectorizer, metadata = load_index(customer_id)
    demo_query = "delay" if "customer_a" in folder else "penalty"
    print(f"\n--- Sanity search: '{demo_query}' ---")
    for r in search(demo_query, index, vectorizer, metadata, top_k=2):
        print(f"  [{r['source_file']} | {r['locator']}] (dist={r['distance']:.3f})")
        print(f"    {r['text'][:120]}...")
