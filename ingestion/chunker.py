"""
chunker.py
Turns parsed file content + its auto-config decision into a list of text
chunks ready for embedding. Each chunk carries metadata (filename + a
locator like row index or page number) so later retrieval can cite the
exact source.
"""

from typing import Dict, Any, List


def chunk_tabular(parsed: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    df = parsed["dataframe"]
    rows_per_chunk = config["rows_per_chunk"]
    chunks = []

    for start in range(0, len(df), rows_per_chunk):
        group = df.iloc[start:start + rows_per_chunk]
        # Render each row as "col: value, col: value, ..." joined across
        # rows in the group -- simple, readable, and embeddable as text.
        row_texts = []
        for _, row in group.iterrows():
            row_texts.append(
                ", ".join(f"{col}: {row[col]}" for col in df.columns)
            )
        text = "\n".join(row_texts)

        chunks.append({
            "text": text,
            "source_file": parsed["filename"],
            "locator": f"rows {start}-{start + len(group) - 1}",
        })

    return chunks


def _sliding_window(text: str, chunk_size: int, overlap: int) -> List[str]:
    if not text:
        return []
    step = max(chunk_size - overlap, 1)
    return [text[i:i + chunk_size] for i in range(0, len(text), step) if text[i:i + chunk_size].strip()]


def chunk_pdf(parsed: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunk_size = config["chunk_size"]
    overlap = config["chunk_overlap"]
    chunks = []

    for page_num, page_text in enumerate(parsed["pages_text"], start=1):
        for window in _sliding_window(page_text, chunk_size, overlap):
            chunks.append({
                "text": window,
                "source_file": parsed["filename"],
                "locator": f"page {page_num}",
            })

    return chunks


def chunk_text(parsed: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunk_size = config["chunk_size"]
    overlap = config["chunk_overlap"]
    chunks = []

    for window in _sliding_window(parsed["content"], chunk_size, overlap):
        chunks.append({
            "text": window,
            "source_file": parsed["filename"],
            "locator": "n/a",
        })

    return chunks


def chunk_file(parsed: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    kind = parsed["kind"]
    if kind == "tabular":
        return chunk_tabular(parsed, config)
    if kind == "pdf":
        return chunk_pdf(parsed, config)
    if kind == "text":
        return chunk_text(parsed, config)
    raise ValueError(f"No chunker for kind: {kind}")
