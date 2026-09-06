"""
parsers.py
Turns a RoutedFile into structured content:
  - tabular -> pandas DataFrame + schema
  - pdf     -> per-page text (+ detected tables)
  - text    -> raw text

Each parse_* function returns a plain dict so it's easy to serialize to
JSON for the profiling step and, later, the chunking step.
"""

from typing import Dict, Any, List
import pandas as pd
import pdfplumber

from ingestion.router import RoutedFile


def parse_tabular(file: RoutedFile) -> Dict[str, Any]:
    if file.ext == ".csv":
        df = pd.read_csv(file.path)
    else:  # .xlsx / .xls
        df = pd.read_excel(file.path)

    return {
        "filename": file.filename,
        "kind": "tabular",
        "dataframe": df,
        "schema": {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        },
    }


def parse_pdf(file: RoutedFile) -> Dict[str, Any]:
    pages_text: List[str] = []
    tables_detected = 0

    with pdfplumber.open(file.path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

            tables = page.extract_tables()
            tables_detected += len(tables)

    return {
        "filename": file.filename,
        "kind": "pdf",
        "pages_text": pages_text,
        "page_count": len(pages_text),
        "tables_detected": tables_detected,
    }


def parse_text(file: RoutedFile) -> Dict[str, Any]:
    with open(file.path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    return {
        "filename": file.filename,
        "kind": "text",
        "content": content,
    }


def parse_file(file: RoutedFile) -> Dict[str, Any]:
    if file.kind == "tabular":
        return parse_tabular(file)
    if file.kind == "pdf":
        return parse_pdf(file)
    if file.kind == "text":
        return parse_text(file)
    raise ValueError(f"No parser for unsupported file: {file.filename}")
