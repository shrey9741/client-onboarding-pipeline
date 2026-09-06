"""
profiler.py
Computes lightweight statistics on each parsed file. This profile is the
input Week 2's auto-config logic will use to pick chunk size, chunking
strategy, and retrieval approach per file / per customer.
"""

from typing import Dict, Any


def profile_tabular(parsed: Dict[str, Any]) -> Dict[str, Any]:
    df = parsed["dataframe"]
    null_pct = (df.isnull().sum() / max(len(df), 1) * 100).round(2).to_dict()

    return {
        "filename": parsed["filename"],
        "kind": "tabular",
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": parsed["schema"]["columns"],
        "dtypes": parsed["schema"]["dtypes"],
        "null_pct_by_column": null_pct,
    }


def profile_pdf(parsed: Dict[str, Any]) -> Dict[str, Any]:
    pages = parsed["pages_text"]
    page_count = parsed["page_count"]
    total_chars = sum(len(p) for p in pages)
    avg_chars_per_page = round(total_chars / page_count, 1) if page_count else 0

    return {
        "filename": parsed["filename"],
        "kind": "pdf",
        "page_count": page_count,
        "total_chars": total_chars,
        "avg_chars_per_page": avg_chars_per_page,
        "tables_detected": parsed["tables_detected"],
        "text_density": "dense" if avg_chars_per_page > 1500 else "sparse",
    }


def profile_text(parsed: Dict[str, Any]) -> Dict[str, Any]:
    content = parsed["content"]
    return {
        "filename": parsed["filename"],
        "kind": "text",
        "char_count": len(content),
        "line_count": content.count("\n") + 1,
    }


def profile_file(parsed: Dict[str, Any]) -> Dict[str, Any]:
    kind = parsed["kind"]
    if kind == "tabular":
        return profile_tabular(parsed)
    if kind == "pdf":
        return profile_pdf(parsed)
    if kind == "text":
        return profile_text(parsed)
    raise ValueError(f"No profiler for kind: {kind}")


def profile_customer(parsed_files) -> Dict[str, Any]:
    """
    parsed_files: list of parsed dicts (from parsers.parse_file)
    Returns a per-file profile list plus a rollup summary.
    """
    file_profiles = [profile_file(p) for p in parsed_files]

    summary = {
        "total_files": len(file_profiles),
        "tabular_files": sum(1 for f in file_profiles if f["kind"] == "tabular"),
        "pdf_files": sum(1 for f in file_profiles if f["kind"] == "pdf"),
        "text_files": sum(1 for f in file_profiles if f["kind"] == "text"),
    }

    return {"files": file_profiles, "summary": summary}
