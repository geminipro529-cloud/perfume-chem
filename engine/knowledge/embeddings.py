"""Vector embeddings and semantic search over perfume knowledge files.

Chunks knowledge/.md and scientific_reference_*.txt files into ~500-char segments,
generates embeddings with sentence-transformers, stores in FAISS index.

Usage:
    from engine.knowledge import KnowledgeIndex
    idx = KnowledgeIndex()
    idx.build()                         # first time only — builds + saves index
    results = idx.search("Roudnitska transparency", k=5)
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "embeddings"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
CHUNK_SIZE = 500   # target chars per chunk
CHUNK_OVERLAP = 80  # overlap between chunks for context continuity
MODEL_NAME = "all-MiniLM-L6-v2"  # ~80MB, runs on CPU


def _collect_source_files() -> list[Path]:
    """Collect all files to index."""
    files = []

    # knowledge/**/*.md
    if KNOWLEDGE_DIR.exists():
        files.extend(sorted(KNOWLEDGE_DIR.rglob("*.md")))

    # scientific_reference_*.txt (combined ones only, e.g. _A_B_C_D.txt)
    for f in sorted(PROJECT_ROOT.glob("scientific_reference_*_*.txt")):
        files.append(f)

    # Accord library and architecture template
    for name in ["perfume_accord_library.txt", "perfume_formula_architecture_template.txt"]:
        p = PROJECT_ROOT / name
        if p.exists():
            files.append(p)

    return files


def _chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks of ~CHUNK_SIZE chars.

    Each chunk: {text, source, chunk_idx}
    Splits preferentially at paragraph boundaries (double newline) or sentence ends.
    """
    # Clean text
    text = text.replace('\r\n', '\n').strip()
    if not text:
        return []

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        if end >= len(text):
            # Last chunk
            chunk_text = text[start:].strip()
            if chunk_text:
                chunks.append({"text": chunk_text, "source": source, "chunk_idx": idx})
            break

        # Try to find a good break point
        segment = text[start:end + 100]  # look ahead a bit

        # Prefer paragraph break
        para_break = segment.rfind('\n\n', CHUNK_SIZE // 2)
        if para_break > 0:
            end = start + para_break + 2
        else:
            # Prefer sentence end
            sent_end = -1
            for pattern in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                pos = segment.rfind(pattern, CHUNK_SIZE // 2)
                if pos > sent_end:
                    sent_end = pos
            if sent_end > 0:
                end = start + sent_end + 2
            else:
                # Fall back to word boundary
                space = segment.rfind(' ', CHUNK_SIZE // 2)
                if space > 0:
                    end = start + space + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "source": source, "chunk_idx": idx})
            idx += 1

        start = end - CHUNK_OVERLAP  # overlap for context

    return chunks


class KnowledgeIndex:
    """FAISS-backed semantic search index over perfume knowledge."""

    def __init__(self):
        self._index = None      # FAISS index
        self._chunks = None     # list of chunk dicts
        self._model = None      # sentence-transformer model
        self._use_faiss = True

    def _load_model(self):
        """Lazy-load the sentence-transformer model."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for semantic search. "
                "Install with: pip install sentence-transformers faiss-cpu"
            )

    def build(self, force: bool = False) -> dict:
        """Build (or rebuild) the FAISS index from knowledge files.

        Returns: {n_files, n_chunks, index_path}
        """
        import numpy as np

        self._load_model()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        index_path = DATA_DIR / "knowledge_index.faiss"
        chunk_path = DATA_DIR / "chunk_map.json"

        if not force and index_path.exists() and chunk_path.exists():
            self._load_index()
            return {
                "n_files": len(set(c["source"] for c in self._chunks)),
                "n_chunks": len(self._chunks),
                "index_path": str(index_path),
                "status": "loaded_existing",
            }

        # Collect and chunk files
        source_files = _collect_source_files()
        all_chunks = []
        for f in source_files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel_path = str(f.relative_to(PROJECT_ROOT))
            chunks = _chunk_text(text, rel_path)
            all_chunks.extend(chunks)

        if not all_chunks:
            raise ValueError("No knowledge files found to index.")

        # Generate embeddings
        texts = [c["text"] for c in all_chunks]
        embeddings = self._model.encode(texts, show_progress_bar=True, batch_size=16)
        embeddings = np.array(embeddings, dtype="float32")

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings = embeddings / norms

        # Build FAISS index
        try:
            import faiss
            dim = embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)  # inner product = cosine on normalized
            self._index.add(embeddings)
            faiss.write_index(self._index, str(index_path))
            self._use_faiss = True
        except ImportError:
            # Fallback: store embeddings as numpy file
            np.save(str(DATA_DIR / "embeddings.npy"), embeddings)
            self._use_faiss = False

        # Save chunk map
        self._chunks = all_chunks
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=1)

        return {
            "n_files": len(source_files),
            "n_chunks": len(all_chunks),
            "index_path": str(index_path),
            "status": "built",
        }

    def _load_index(self):
        """Load existing index and chunk map from disk."""
        import numpy as np

        chunk_path = DATA_DIR / "chunk_map.json"
        index_path = DATA_DIR / "knowledge_index.faiss"
        npy_path = DATA_DIR / "embeddings.npy"

        with open(chunk_path, "r", encoding="utf-8") as f:
            self._chunks = json.load(f)

        try:
            import faiss
            self._index = faiss.read_index(str(index_path))
            self._use_faiss = True
        except (ImportError, Exception):
            if npy_path.exists():
                self._embeddings_np = np.load(str(npy_path))
                self._use_faiss = False
            else:
                raise FileNotFoundError(
                    "No FAISS index or numpy embeddings found. Run build() first."
                )

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Semantic search over knowledge base.

        Args:
            query: Natural language query
            k: Number of results to return

        Returns: list of {text, source, chunk_idx, score}
        """
        import numpy as np

        self._load_model()

        if self._chunks is None:
            self._load_index()

        # Encode query
        q_emb = self._model.encode([query])
        q_emb = np.array(q_emb, dtype="float32")
        norm = np.linalg.norm(q_emb)
        if norm > 0:
            q_emb = q_emb / norm

        if self._use_faiss:
            scores, indices = self._index.search(q_emb, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                chunk = self._chunks[idx].copy()
                chunk["score"] = float(score)
                results.append(chunk)
        else:
            # Numpy fallback — brute force cosine similarity
            sims = (self._embeddings_np @ q_emb.T).flatten()
            top_k = np.argsort(sims)[::-1][:k]
            results = []
            for idx in top_k:
                chunk = self._chunks[idx].copy()
                chunk["score"] = float(sims[idx])
                results.append(chunk)

        return results

    def search_with_context(self, query: str, k: int = 5, context_chunks: int = 1) -> list[dict]:
        """Search and include surrounding chunks for context.

        Args:
            query: Natural language query
            k: Number of results
            context_chunks: Number of chunks before/after to include

        Returns: list of {text, source, chunk_idx, score, context_before, context_after}
        """
        results = self.search(query, k)

        for r in results:
            source = r["source"]
            idx = r["chunk_idx"]

            # Find adjacent chunks from same source
            same_source = [c for c in self._chunks if c["source"] == source]
            same_source.sort(key=lambda c: c["chunk_idx"])

            before_texts = []
            after_texts = []
            for c in same_source:
                if idx - context_chunks <= c["chunk_idx"] < idx:
                    before_texts.append(c["text"])
                elif idx < c["chunk_idx"] <= idx + context_chunks:
                    after_texts.append(c["text"])

            r["context_before"] = "\n".join(before_texts)
            r["context_after"] = "\n".join(after_texts)

        return results
