"""Tiny TF-IDF index + numpy cosine search (no neural embedder)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "with",
        "from",
        "that",
        "this",
        "it",
        "as",
        "has",
        "have",
        "had",
    }
)


def tokenize(text: str) -> list[str]:
    words = [
        w
        for w in TOKEN_RE.findall((text or "").lower())
        if w not in STOPWORDS and len(w) > 1
    ]
    grams = list(words)
    grams.extend(f"{a}_{b}" for a, b in zip(words, words[1:]))
    return grams


def _term_counts(tokens: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tok in tokens:
        counts[tok] = counts.get(tok, 0) + 1
    return counts


@dataclass(frozen=True)
class TfidfIndex:
    vocab: dict[str, int]
    idf: np.ndarray
    matrix: np.ndarray  # L2-normalized rows, shape (n_docs, n_terms)
    labels: tuple[str, ...]
    ids: tuple[str, ...]
    catalog_version: int


def build_index(
    exemplars: Iterable[dict[str, Any]],
    *,
    catalog_version: int = 1,
) -> TfidfIndex:
    docs = list(exemplars)
    if not docs:
        raise ValueError("pre-router catalog has no exemplars")
    tokenized = [tokenize(str(row.get("text") or "")) for row in docs]
    df: dict[str, int] = {}
    for toks in tokenized:
        for term in set(toks):
            df[term] = df.get(term, 0) + 1
    vocab = {term: i for i, term in enumerate(sorted(df))}
    n_docs = len(docs)
    n_terms = len(vocab)
    idf = np.zeros(n_terms, dtype=np.float64)
    for term, idx in vocab.items():
        idf[idx] = math.log((n_docs + 1.0) / (df[term] + 1.0)) + 1.0
    matrix = np.zeros((n_docs, n_terms), dtype=np.float64)
    for row_i, toks in enumerate(tokenized):
        counts = _term_counts(toks)
        for term, tf in counts.items():
            col = vocab.get(term)
            if col is None:
                continue
            matrix[row_i, col] = (1.0 + math.log(tf)) * idf[col]
        norm = np.linalg.norm(matrix[row_i])
        if norm > 0:
            matrix[row_i] /= norm
    labels = tuple(str(row["label"]) for row in docs)
    ids = tuple(str(row.get("id") or f"ex-{i}") for i, row in enumerate(docs))
    return TfidfIndex(
        vocab=vocab,
        idf=idf,
        matrix=matrix,
        labels=labels,
        ids=ids,
        catalog_version=catalog_version,
    )


def embed_query(text: str, index: TfidfIndex) -> np.ndarray:
    vec = np.zeros(len(index.vocab), dtype=np.float64)
    counts = _term_counts(tokenize(text))
    for term, tf in counts.items():
        col = index.vocab.get(term)
        if col is None:
            continue
        vec[col] = (1.0 + math.log(tf)) * index.idf[col]
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def cosine_search(text: str, index: TfidfIndex) -> dict[str, Any]:
    query = embed_query(text, index)
    if not np.any(query):
        return {
            "score": 0.0,
            "margin": 0.0,
            "label": None,
            "matched_exemplar_id": None,
            "second_label": None,
            "second_score": 0.0,
            "scores_by_label": {},
        }
    scores = index.matrix @ query
    order = np.argsort(scores)[::-1]
    top = int(order[0])
    second = int(order[1]) if len(order) > 1 else top
    by_label: dict[str, float] = {}
    for label, score in zip(index.labels, scores.tolist()):
        prev = by_label.get(label)
        if prev is None or score > prev:
            by_label[label] = float(score)
    return {
        "score": float(scores[top]),
        "margin": float(scores[top] - scores[second]),
        "label": index.labels[top],
        "matched_exemplar_id": index.ids[top],
        "second_label": index.labels[second],
        "second_score": float(scores[second]),
        "scores_by_label": by_label,
    }
