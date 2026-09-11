"""
onboard.py
Week 5: the "one command" entry point. Wraps everything from Weeks 1-2
(route -> parse -> profile -> auto_config -> chunk -> embed -> index)
into a single function, so both the CLI script and the Streamlit UI
call the exact same pipeline logic instead of duplicating it.
"""

import os
import json

from ingestion.router import route_folder
from ingestion.parsers import parse_file
from ingestion.profiler import profile_customer
from ingestion.auto_config import configure_customer
from ingestion.chunker import chunk_file
from ingestion.embedder import build_index, save_index


def onboard_client(folder_path: str, output_dir: str = "output", progress_callback=None):
    """
    Runs the full ingestion + indexing pipeline for one customer folder.

    progress_callback, if given, is called with a short status string after
    each stage -- lets a UI show live progress without this function
    knowing anything about how it's displayed.

    Returns a summary dict: customer_id, file counts, chunk count,
    flagged files, and the paths where results were saved.
    """
    def notify(msg):
        if progress_callback:
            progress_callback(msg)

    notify("Routing files...")
    routing = route_folder(folder_path)

    notify("Parsing files...")
    parsed_files = []
    for f in routing.all_files():
        if f.kind == "unsupported":
            continue
        parsed_files.append(parse_file(f))

    notify("Profiling data...")
    profile = profile_customer(parsed_files)

    notify("Auto-configuring chunk strategy...")
    config_result = configure_customer(profile)
    config_by_filename = {c["filename"]: c for c in config_result["configs"]}

    notify("Chunking...")
    all_chunks = []
    for parsed in parsed_files:
        cfg = config_by_filename[parsed["filename"]]
        all_chunks.extend(chunk_file(parsed, cfg))

    notify("Embedding + building index...")
    index, vectorizer, metadata = build_index(all_chunks)
    save_index(routing.customer_id, index, vectorizer, metadata, output_dir)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, f"{routing.customer_id}_profile.json"), "w") as f:
        json.dump(profile, f, indent=2, default=str)
    with open(os.path.join(output_dir, f"{routing.customer_id}_config.json"), "w") as f:
        json.dump(config_result, f, indent=2)

    notify("Done.")

    return {
        "customer_id": routing.customer_id,
        "file_count": len(parsed_files),
        "chunk_count": len(all_chunks),
        "flagged_for_cleaning": config_result["flagged_for_cleaning"],
        "configs": config_result["configs"],
        "output_dir": os.path.join(output_dir, routing.customer_id),
    }


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "samples/customer_a"
    summary = onboard_client(folder, progress_callback=print)
    print(json.dumps(summary, indent=2, default=str))
