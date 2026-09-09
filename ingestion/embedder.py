"""
embedder.py
Embeds a customer's chunks and builds a FAISS index for retrieval.

Uses TF-IDF (scikit-learn) rather than a downloaded neural embedding model
by default -- it's dependency-light, fully local/offline, and keeps this
stage testable without pulling large model weights. The FAISS index is
embedding-agnostic: swap in sentence-transformers later (Week 3+) by
changing only `build_index()` if you want denser semantic retrieval;
everything downstream (index, metadata, search) stays the same.
"""

import os
import json
import pickle
from typing import List, Dict, Any

import numpy as np
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer


def build_index(chunks: List[Dict[str, Any]]):
    """
    chunks: list of {"text": ..., "source_file": ..., "locator": ...}
    Returns (faiss_index, vectorizer, chunk_metadata)
    """
    texts = [c["text"] for c in chunks]

    # Default token pattern treats underscores as part of a word, so a
    # column name like "avg_delay_days" stays one token and a query for
    # "delay" would never match it. Splitting on letters only fixes that.
    vectorizer = TfidfVectorizer(max_features=4096, token_pattern=r"(?u)[A-Za-z]+")
    tfidf_matrix = vectorizer.fit_transform(texts).toarray().astype("float32")

    dim = tfidf_matrix.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(tfidf_matrix)

    metadata = [
        {"source_file": c["source_file"], "locator": c["locator"], "text": c["text"]}
        for c in chunks
    ]

    return index, vectorizer, metadata


def save_index(customer_id: str, index, vectorizer, metadata: List[Dict[str, Any]], output_dir: str = "output"):
    customer_dir = os.path.join(output_dir, customer_id)
    os.makedirs(customer_dir, exist_ok=True)

    faiss.write_index(index, os.path.join(customer_dir, "index.faiss"))

    with open(os.path.join(customer_dir, "vectorizer.pkl"), "wb") as f:
        pickle.dump(vectorizer, f)

    with open(os.path.join(customer_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    return customer_dir


def load_index(customer_id: str, output_dir: str = "output"):
    customer_dir = os.path.join(output_dir, customer_id)
    index_path = os.path.join(customer_dir, "index.faiss")

    if not os.path.isfile(index_path):
        raise FileNotFoundError(f"No FAISS index found for customer '{customer_id}' at {index_path}")

    index = faiss.read_index(index_path)

    with open(os.path.join(customer_dir, "vectorizer.pkl"), "rb") as f:
        vectorizer = pickle.load(f)

    with open(os.path.join(customer_dir, "metadata.json"), "r") as f:
        metadata = json.load(f)

    return index, vectorizer, metadata


def search(query: str, index, vectorizer, metadata: List[Dict[str, Any]], top_k: int = 3):
    query_vec = vectorizer.transform([query]).toarray().astype("float32")
    distances, indices = index.search(query_vec, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        results.append({**metadata[idx], "distance": float(dist)})

    return results
