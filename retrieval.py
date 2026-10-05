"""retrieval.py - Stage 3: turn chunks into embeddings and search them."""

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

_model = None


def get_model():
    """Load the embedding model once (the first run downloads it)."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def build_index(chunks):
    """Embed every chunk and put the vectors in a FAISS index."""
    texts = [c["text"] for c in chunks]
    vecs = get_model().encode(
        texts, normalize_embeddings=True, show_progress_bar=False
    )
    vecs = np.array(vecs, dtype="float32")
    index = faiss.IndexFlatIP(vecs.shape[1])  # inner product = cosine similarity
    index.add(vecs)
    return index


def search(question, index, chunks, k=4):
    """Return the top-k chunks for a question, each with a 'score' (0 to 1)."""
    q = get_model().encode([question], normalize_embeddings=True)
    q = np.array(q, dtype="float32")
    k = min(k, len(chunks))
    scores, ids = index.search(q, k)

    results = []
    for score, i in zip(scores[0], ids[0]):
        if i == -1:
            continue
        item = dict(chunks[i])
        item["score"] = float(score)
        results.append(item)
    return results