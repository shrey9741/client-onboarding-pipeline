"""
onboard.py
Week 5: the "one command" entry point. Wraps everything from Weeks 1-2
(route -> parse -> profile -> auto_config -> chunk -> embed -> index)
into a single function, so both the CLI script and the API call the
exact same pipeline logic instead of duplicating it.

Progress is reported as structured (stage_key, status, detail) events,
not just printable strings, so a caller (like the FastAPI backend) can
track real per-stage state for a UI to poll -- not a fake progress bar.
"""

import os
import json

from ingestion.router import route_folder
from ingestion.parsers import parse_file
from ingestion.profiler import profile_customer
from ingestion.auto_config import configure_customer
from ingestion.chunker import chunk_file
from ingestion.embedder import build_index, save_index

STAGE_ORDER = ["route", "parse", "profile", "config", "chunk", "index"]


def onboard_client(folder_path: str, output_dir: str = "output", on_stage=None):
    """
    Runs the full ingestion + indexing pipeline for one customer folder.

    on_stage(stage_key, status, detail=None), if given, is called at the
    start ("running") and end ("done") of each stage in STAGE_ORDER, plus
    a final ("done", "done") event when the whole pipeline finishes.

    Returns a summary dict: customer_id, file counts, chunk count,
    flagged files, and the paths where results were saved.
    """
    def notify(stage_key, status, detail=None):
        if on_stage:
            on_stage(stage_key, status, detail)

    notify("route", "running")
    routing = route_folder(folder_path)
    notify("route", "done", detail=f"{len(routing.all_files())} file(s) routed")

    notify("parse", "running")
    parsed_files = []
    for f in routing.all_files():
        if f.kind == "unsupported":
            continue
        parsed_files.append(parse_file(f))
    notify("parse", "done", detail=f"{len(parsed_files)} file(s) parsed")

    notify("profile", "running")
    profile = profile_customer(parsed_files)
    notify("profile", "done")

    notify("config", "running")
    config_result = configure_customer(profile)
    config_by_filename = {c["filename"]: c for c in config_result["configs"]}
    flagged = config_result["flagged_for_cleaning"]
    notify("config", "done", detail=f"{len(flagged)} file(s) flagged for cleaning")

    notify("chunk", "running")
    all_chunks = []
    for parsed in parsed_files:
        cfg = config_by_filename[parsed["filename"]]
        all_chunks.extend(chunk_file(parsed, cfg))
    notify("chunk", "done", detail=f"{len(all_chunks)} chunk(s) created")

    notify("index", "running")
    index, vectorizer, metadata = build_index(all_chunks)
    save_index(routing.customer_id, index, vectorizer, metadata, output_dir)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, f"{routing.customer_id}_profile.json"), "w") as f:
        json.dump(profile, f, indent=2, default=str)
    with open(os.path.join(output_dir, f"{routing.customer_id}_config.json"), "w") as f:
        json.dump(config_result, f, indent=2)
    notify("index", "done")

    notify("done", "done")

    return {
        "customer_id": routing.customer_id,
        "file_count": len(parsed_files),
        "chunk_count": len(all_chunks),
        "flagged_for_cleaning": flagged,
        "configs": config_result["configs"],
        "output_dir": os.path.join(output_dir, routing.customer_id),
    }


if __name__ == "__main__":
    import sys

    def cli_progress(stage_key, status, detail=None):
        line = f"[{stage_key}] {status}"
        if detail:
            line += f" - {detail}"
        print(line)

    folder = sys.argv[1] if len(sys.argv) > 1 else "samples/customer_a"
    summary = onboard_client(folder, on_stage=cli_progress)
    print(json.dumps(summary, indent=2, default=str))
