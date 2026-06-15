"""Similar Plan Service (component 1).

Provides planning precedents only -- never answers or data. Implements
the architecture doc's hybrid retrieval:

* Stage 1: metadata filtering (dataset family overlap with the domain).
* Stage 2: BM25 (lexical) + embedding cosine similarity (semantic).
* Stage 3: weighted score fusion (weighted sum or RRF), normalized to
  [0, 1] and used as the ``confidence`` of each matched pattern.
"""

import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import yaml
from rank_bm25 import BM25Okapi

from ic_agent.config.probe_budget import ScoreFusionWeights
from ic_agent.models.similar_plan import MatchedPattern, SimilarPlanEntry, SimilarPlanQuery, SimilarPlanResult
from ic_agent.services.embeddings import EmbeddingBackend

logger = logging.getLogger(__name__)


def _entry_text(entry: SimilarPlanEntry) -> str:
    return " ".join([entry.intent, entry.description, " ".join(entry.probe_sequence)])


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _min_max_normalize(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    lo, hi = float(scores.min()), float(scores.max())
    if hi - lo < 1e-12:
        return np.ones_like(scores) if hi > 0 else np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


class SimilarPlanService:
    def __init__(
        self,
        corpus_path: str | Path,
        score_fusion_weights: ScoreFusionWeights | None = None,
        embedding_backend: EmbeddingBackend | None = None,
        top_k: int = 3,
        cache_dir: str | Path | None = None,
    ):
        self._weights = score_fusion_weights or ScoreFusionWeights()
        self._embedding_backend = embedding_backend
        self._top_k = top_k

        self._corpus_path = Path(corpus_path)
        self._cache_dir = Path(cache_dir) if cache_dir else self._corpus_path.parent / ".cache"

        self._entries: list[SimilarPlanEntry] = self._load_corpus()
        self._corpus_texts = [_entry_text(e) for e in self._entries]
        self._bm25 = BM25Okapi([_tokenize(t) for t in self._corpus_texts]) if self._entries else None
        self._embeddings: list[list[float]] | None = None

    def _load_corpus(self) -> list[SimilarPlanEntry]:
        if not self._corpus_path.exists():
            logger.warning("Similar plan corpus not found at %s; corpus is empty", self._corpus_path)
            return []

        with self._corpus_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []

        return [SimilarPlanEntry.model_validate(item) for item in data]

    def _corpus_hash(self) -> str:
        digest_input = "␟".join(self._corpus_texts).encode("utf-8")
        return hashlib.sha256(digest_input).hexdigest()[:16]

    def _get_embeddings(self) -> list[list[float]] | None:
        if self._embedding_backend is None or not self._corpus_texts:
            return None
        if self._embeddings is not None:
            return self._embeddings

        cache_file = self._cache_dir / f"embeddings_{self._corpus_hash()}.json"
        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                self._embeddings = json.load(f)
            return self._embeddings

        self._embeddings = self._embedding_backend.embed_documents(self._corpus_texts)

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(self._embeddings, f)

        return self._embeddings

    def _metadata_filter(self, query: SimilarPlanQuery) -> list[int]:
        """Stage 1: keep entries whose dataset_family overlaps with the
        domain's datasets. Falls back to the full corpus if nothing matches."""
        domain_datasets = {d.name for d in query.domain_context.datasets}
        if not domain_datasets:
            return list(range(len(self._entries)))

        filtered = [
            i
            for i, entry in enumerate(self._entries)
            if domain_datasets.intersection(entry.dataset_family)
        ]
        return filtered if filtered else list(range(len(self._entries)))

    def search(self, query: SimilarPlanQuery) -> SimilarPlanResult:
        if not self._entries:
            return SimilarPlanResult(matched_patterns=[])

        candidate_indices = self._metadata_filter(query)

        bm25_scores = np.array(self._bm25.get_scores(_tokenize(query.user_query)))
        bm25_candidates = bm25_scores[candidate_indices]
        norm_bm25 = _min_max_normalize(bm25_candidates)

        embeddings = self._get_embeddings()
        if embeddings is not None:
            query_vec = np.array(self._embedding_backend.embed_query(query.user_query))
            emb_candidates = np.array([embeddings[i] for i in candidate_indices])
            norms = np.linalg.norm(emb_candidates, axis=1) * np.linalg.norm(query_vec)
            norms[norms == 0] = 1e-12
            emb_scores = (emb_candidates @ query_vec) / norms
            norm_emb = _min_max_normalize(emb_scores)
        else:
            norm_emb = np.zeros_like(norm_bm25)

        if self._weights.fusion_method == "rrf":
            bm25_ranks = (-bm25_candidates).argsort().argsort()
            emb_ranks = (-norm_emb).argsort().argsort() if embeddings is not None else bm25_ranks
            k = self._weights.rrf_k
            fused = 1.0 / (k + bm25_ranks + 1) + (
                1.0 / (k + emb_ranks + 1) if embeddings is not None else 0.0
            )
        else:
            fused = self._weights.bm25_weight * norm_bm25 + self._weights.embedding_weight * norm_emb

        confidence = _min_max_normalize(fused)

        order = np.argsort(-fused)[: self._top_k]

        matched: list[MatchedPattern] = []
        for rank in order:
            idx = candidate_indices[rank]
            entry = self._entries[idx]
            matched.append(
                MatchedPattern(
                    pattern_id=entry.id,
                    confidence=round(float(confidence[rank]), 4),
                    reason=(
                        f"Matched on intent '{entry.intent}' "
                        f"(bm25={float(norm_bm25[rank]):.3f}, embedding={float(norm_emb[rank]):.3f})"
                    ),
                    probe_strategy=entry.probe_sequence,
                )
            )

        logger.info(
            "SimilarPlanService: %d candidates after metadata filter, top match=%s",
            len(candidate_indices),
            matched[0].pattern_id if matched else None,
        )

        return SimilarPlanResult(matched_patterns=matched)
