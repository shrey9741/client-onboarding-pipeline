"""
auto_config.py
Week 2: reads a file's profile (from profiler.py) and decides HOW to chunk
it — strategy, chunk size, overlap — plus flags data quality issues that
should block or warn before embedding.

This is the "adapts to any client's data" core of the pipeline: two
structurally different files should come out of here with two different,
justified configs.
"""

from typing import Dict, Any

# Thresholds are intentionally named constants, not magic numbers, so the
# reasoning is easy to explain in an interview / README.
HIGH_NULL_THRESHOLD_PCT = 15.0
DENSE_PDF_CHARS_PER_PAGE = 1500
LARGE_TABLE_ROW_THRESHOLD = 5000


def configure_tabular(profile: Dict[str, Any]) -> Dict[str, Any]:
    null_pct_by_col = profile.get("null_pct_by_column", {})
    max_null_pct = max(null_pct_by_col.values()) if null_pct_by_col else 0.0
    needs_cleaning = max_null_pct > HIGH_NULL_THRESHOLD_PCT

    row_count = profile["row_count"]
    # Large tables get grouped a few rows per chunk to keep the index
    # smaller; small tables get one row per chunk for precise retrieval.
    rows_per_chunk = 5 if row_count > LARGE_TABLE_ROW_THRESHOLD else 1

    reasons = [
        f"tabular file with {row_count} rows -> row-level chunking "
        f"({rows_per_chunk} row(s) per chunk)"
    ]
    if needs_cleaning:
        reasons.append(
            f"max null% across columns is {max_null_pct:.1f}% (> "
            f"{HIGH_NULL_THRESHOLD_PCT}%) -> flagged for cleaning before embedding"
        )

    return {
        "filename": profile["filename"],
        "kind": "tabular",
        "strategy": "row_level",
        "rows_per_chunk": rows_per_chunk,
        "needs_cleaning": needs_cleaning,
        "max_null_pct": max_null_pct,
        "reason": "; ".join(reasons),
    }


def configure_pdf(profile: Dict[str, Any]) -> Dict[str, Any]:
    is_dense = profile["avg_chars_per_page"] > DENSE_PDF_CHARS_PER_PAGE
    has_tables = profile["tables_detected"] > 0

    if is_dense:
        chunk_size, overlap = 500, 100
    else:
        chunk_size, overlap = 1000, 150

    reasons = [
        f"{'dense' if is_dense else 'sparse'} text "
        f"({profile['avg_chars_per_page']:.0f} chars/page) -> "
        f"chunk_size={chunk_size}, overlap={overlap}"
    ]
    if has_tables:
        reasons.append(
            f"{profile['tables_detected']} table(s) detected -> "
            f"flagged for table-aware handling"
        )

    return {
        "filename": profile["filename"],
        "kind": "pdf",
        "strategy": "sliding_window",
        "chunk_size": chunk_size,
        "chunk_overlap": overlap,
        "has_tables": has_tables,
        "reason": "; ".join(reasons),
    }


def configure_text(profile: Dict[str, Any]) -> Dict[str, Any]:
    # Free-form notes are short and low-structure; a single generic
    # window size is enough, no need for density-based branching.
    chunk_size, overlap = 800, 100

    return {
        "filename": profile["filename"],
        "kind": "text",
        "strategy": "sliding_window",
        "chunk_size": chunk_size,
        "chunk_overlap": overlap,
        "reason": (
            f"free-form text ({profile['char_count']} chars) -> "
            f"fixed chunk_size={chunk_size}, overlap={overlap}"
        ),
    }


def configure_file(profile: Dict[str, Any]) -> Dict[str, Any]:
    kind = profile["kind"]
    if kind == "tabular":
        return configure_tabular(profile)
    if kind == "pdf":
        return configure_pdf(profile)
    if kind == "text":
        return configure_text(profile)
    raise ValueError(f"No auto-config rule for kind: {kind}")


def configure_customer(customer_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    customer_profile: the dict produced by profiler.profile_customer()
    Returns a list of per-file configs plus a rollup.
    """
    file_configs = [configure_file(f) for f in customer_profile["files"]]

    flagged_for_cleaning = [
        c["filename"] for c in file_configs if c.get("needs_cleaning")
    ]

    return {
        "configs": file_configs,
        "flagged_for_cleaning": flagged_for_cleaning,
    }
