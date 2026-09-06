"""
run_ingestion.py
Week 1 checkpoint script.

Usage:
    python run_ingestion.py samples/customer_a
    python run_ingestion.py samples/customer_b

Runs: route_folder -> parse_file (per file) -> profile_customer
Saves a JSON profiling report to output/<customer_id>_profile.json
"""

import sys
import json
import os

from ingestion.router import route_folder, print_routing_summary
from ingestion.parsers import parse_file
from ingestion.profiler import profile_customer


def run(folder_path: str, output_dir: str = "output"):
    routing = route_folder(folder_path)
    print_routing_summary(routing)

    parsed_files = []
    for f in routing.all_files():
        if f.kind == "unsupported":
            print(f"  Skipping unsupported file: {f.filename}")
            continue
        print(f"  Parsing: {f.filename} ({f.kind})")
        parsed_files.append(parse_file(f))

    profile = profile_customer(parsed_files)

    print("\n--- Profile Summary ---")
    print(json.dumps(profile["summary"], indent=2))
    print("\n--- Per-file Profile ---")
    print(json.dumps(profile["files"], indent=2, default=str))

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{routing.customer_id}_profile.json")
    with open(out_path, "w") as f:
        json.dump(profile, f, indent=2, default=str)

    print(f"\nSaved profile report -> {out_path}")
    return profile


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "samples/customer_a"
    run(folder)
