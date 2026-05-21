"""
FAISS vector store service for semantic question similarity search.
Falls back to TF-IDF if sentence-transformers or FAISS are not available.
"""
import json
import logging
import os
import pickle
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Manages a vector index over the question bank for semantic search.
    Tries FAISS + sentence-transformers first; falls back to TF-IDF + cosine similarity.
    """

    def __init__(self):
        self.questions: List[Dict[str, Any]] = []
        self.index = None
        self.embeddings: Optional[np.ndarray] = None
        self.use_faiss = False
        self.use_sentence_transformers = False
        self.vectorizer = None  # TF-IDF fallback
        self._try_import_backends()

    # ─── Backend Detection ────────────────────────────────────────────────────

    def _try_import_backends(self):
        # Intentionally skip sentence-transformers to avoid model downloads.
        # TF-IDF + cosine similarity works offline with no setup required.
        self.use_faiss = False
        self.use_sentence_transformers = False
        try:
            import faiss  # noqa: F401
            self.use_faiss = True
            logger.info("FAISS backend available.")
        except ImportError:
            logger.info("FAISS not available; using numpy cosine similarity.")
        # sentence-transformers intentionally disabled — requires internet download
        logger.info("Using TF-IDF vector backend (offline, no download required).")

    # ─── Index Building ───────────────────────────────────────────────────────

    def build_index(self, questions: List[Dict[str, Any]]):
        """Build the vector index from a list of question dicts."""
        self.questions = questions
        texts = [q["text"] for q in questions]

        if self.use_sentence_transformers:
            self.embeddings = self._encode_with_st(texts)
        else:
            self.embeddings = self._encode_with_tfidf(texts)

        if self.use_faiss and self.embeddings is not None:
            self._build_faiss_index()
        logger.info(f"Vector index built with {len(questions)} questions.")

    def _encode_with_st(self, texts: List[str]) -> np.ndarray:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(texts, convert_to_numpy=True).astype("float32")

    def _encode_with_tfidf(self, texts: List[str]) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=512)
        matrix = self.vectorizer.fit_transform(texts)
        return matrix.toarray().astype("float32")

    def _build_faiss_index(self):
        import faiss
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(self.embeddings)

    # ─── Search ───────────────────────────────────────────────────────────────

    def search_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Return the k most similar questions to the query string."""
        if not self.questions or self.embeddings is None:
            return []

        query_vec = self._encode_query(query)

        if self.use_faiss and self.index is not None:
            return self._faiss_search(query_vec, k)
        return self._numpy_search(query_vec, k)

    def _encode_query(self, query: str) -> np.ndarray:
        if self.use_sentence_transformers:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            return model.encode([query], convert_to_numpy=True).astype("float32")
        if self.vectorizer is not None:
            return self.vectorizer.transform([query]).toarray().astype("float32")
        # Last resort: zero vector
        return np.zeros((1, self.embeddings.shape[1]), dtype="float32")

    def _faiss_search(self, query_vec: np.ndarray, k: int) -> List[Dict[str, Any]]:
        import faiss  # noqa: F401
        k = min(k, len(self.questions))
        _, indices = self.index.search(query_vec, k)
        return [self.questions[i] for i in indices[0] if i < len(self.questions)]

    def _numpy_search(self, query_vec: np.ndarray, k: int) -> List[Dict[str, Any]]:
        """Cosine similarity search using numpy."""
        q = query_vec[0]
        norms = np.linalg.norm(self.embeddings, axis=1)
        q_norm = np.linalg.norm(q)
        if q_norm == 0 or np.any(norms == 0):
            return self.questions[:k]
        similarities = (self.embeddings @ q) / (norms * q_norm + 1e-9)
        top_k = np.argsort(similarities)[::-1][:k]
        return [self.questions[i] for i in top_k]

    # ─── Persistence ──────────────────────────────────────────────────────────

    def save_index(self, path: str):
        """Persist the index and metadata to disk."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        data = {
            "questions": self.questions,
            "embeddings": self.embeddings,
            "vectorizer": self.vectorizer,
        }
        with open(f"{path}.pkl", "wb") as f:
            pickle.dump(data, f)

        if self.use_faiss and self.index is not None:
            import faiss
            faiss.write_index(self.index, f"{path}.faiss")
        logger.info(f"Index saved to {path}.")

    def load_index(self, path: str) -> bool:
        """Load a previously saved index. Returns True on success."""
        pkl_path = f"{path}.pkl"
        if not os.path.exists(pkl_path):
            return False
        try:
            with open(pkl_path, "rb") as f:
                data = pickle.load(f)
            self.questions = data["questions"]
            self.embeddings = data["embeddings"]
            self.vectorizer = data.get("vectorizer")

            faiss_path = f"{path}.faiss"
            if self.use_faiss and os.path.exists(faiss_path):
                import faiss
                self.index = faiss.read_index(faiss_path)
            logger.info(f"Index loaded from {path}.")
            return True
        except Exception as e:
            logger.warning(f"Failed to load index: {e}")
            return False


# Singleton instance
vector_store_service = VectorStoreService()
