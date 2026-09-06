"""
router.py
Scans a customer's raw data folder and classifies each file by type
so the right parser can be applied. This is Day/Week 1 of the pipeline:
Ingestion & Auto-Detection.
"""

import os
from dataclasses import dataclass, field
from typing import List


SUPPORTED_TABULAR = {".csv", ".xlsx", ".xls"}
SUPPORTED_PDF = {".pdf"}
SUPPORTED_TEXT = {".txt", ".md"}


@dataclass
class RoutedFile:
    path: str
    filename: str
    ext: str
    kind: str  # "tabular" | "pdf" | "text" | "unsupported"


@dataclass
class RoutingResult:
    customer_id: str
    tabular: List[RoutedFile] = field(default_factory=list)
    pdf: List[RoutedFile] = field(default_factory=list)
    text: List[RoutedFile] = field(default_factory=list)
    unsupported: List[RoutedFile] = field(default_factory=list)

    def all_files(self) -> List[RoutedFile]:
        return self.tabular + self.pdf + self.text + self.unsupported


def classify_extension(ext: str) -> str:
    ext = ext.lower()
    if ext in SUPPORTED_TABULAR:
        return "tabular"
    if ext in SUPPORTED_PDF:
        return "pdf"
    if ext in SUPPORTED_TEXT:
        return "text"
    return "unsupported"


def route_folder(folder_path: str, customer_id: str = None) -> RoutingResult:
    """
    Walks a folder (non-recursive by default, extend to os.walk if you need
    nested folders) and classifies every file found.
    """
    if customer_id is None:
        customer_id = os.path.basename(os.path.normpath(folder_path))

    result = RoutingResult(customer_id=customer_id)

    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Customer folder not found: {folder_path}")

    for entry in sorted(os.listdir(folder_path)):
        full_path = os.path.join(folder_path, entry)
        if not os.path.isfile(full_path):
            continue

        _, ext = os.path.splitext(entry)
        kind = classify_extension(ext)
        routed = RoutedFile(path=full_path, filename=entry, ext=ext.lower(), kind=kind)

        if kind == "tabular":
            result.tabular.append(routed)
        elif kind == "pdf":
            result.pdf.append(routed)
        elif kind == "text":
            result.text.append(routed)
        else:
            result.unsupported.append(routed)

    return result


def print_routing_summary(result: RoutingResult) -> None:
    print(f"\nCustomer: {result.customer_id}")
    print(f"  Tabular files : {len(result.tabular)} -> {[f.filename for f in result.tabular]}")
    print(f"  PDF files     : {len(result.pdf)} -> {[f.filename for f in result.pdf]}")
    print(f"  Text files    : {len(result.text)} -> {[f.filename for f in result.text]}")
    if result.unsupported:
        print(f"  Unsupported   : {len(result.unsupported)} -> {[f.filename for f in result.unsupported]}")


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "samples/customer_a"
    res = route_folder(folder)
    print_routing_summary(res)
