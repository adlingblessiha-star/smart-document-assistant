"""retrieval.py - Stage 3: turn chunks into embeddings and search them.

This version uses Gemini's embedding model instead of a model running on your
laptop. That means no PyTorch, no sentence-transformers and no FAISS, so there
are no heavy compiled libraries for Windows to block.

How it works:
  1. Every chunk is sent to Gemini, which returns a list of numbers
     (an embedding) describing its meaning.
  2. We store all embeddings as one numpy table, one row per chunk.
  3. For a question, we embed it the same way and take the dot product with
     every row. A higher number means a closer meaning (cosine similarity).
"""

import time

import numpy as np

from llm import get_client

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIMENSIONS = 768      # smaller vectors = faster and lighter, still accurate
BATCH_SIZE = 20             # chunks sent to Gemini per request
RETRY_DELAYS = [2, 5, 10, 20]


def _embed(texts, task_type):
    """Embed a list of texts. Retries on temporary errors (busy / rate limit).

    task_type is "RETRIEVAL_DOCUMENT" for chunks and "RETRIEVAL_QUERY" for
    questions. Gemini embeds them slightly differently so they match better.
    """
    from google.genai import types

    last_error = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            result = get_client().models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBED_DIMENSIONS,
                ),
            )
            return np.array([e.values for e in result.embeddings], dtype="float32")
        except Exception as e:
            last_error = e
            message = str(e)
            is_temporary = any(
                word in message
                for word in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
            )
            if is_temporary and attempt < len(RETRY_DELAYS):
                time.sleep(RETRY_DELAYS[attempt])
                continue
            break
    raise RuntimeError(f"Embedding request failed: {last_error}")


def _normalise(vectors):
    """Scale every vector to length 1, so dot product = cosine similarity."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def build_index(chunks, progress=None):
    """Embed every chunk. Returns a numpy table (one row per chunk).

    `progress`, if given, is called as progress(done, total) after each batch.
    """
    texts = [c["text"] for c in chunks]
    parts = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        parts.append(_embed(batch, "RETRIEVAL_DOCUMENT"))
        if progress:
            progress(min(start + BATCH_SIZE, len(texts)), len(texts))
    return _normalise(np.vstack(parts))


def search(question, index, chunks, k=4):
    """Return the top-k chunks for a question, each with a 'score' (0 to 1)."""
    q = _normalise(_embed([question], "RETRIEVAL_QUERY"))[0]
    scores = index @ q

    k = min(k, len(chunks))
    top_ids = np.argsort(scores)[::-1][:k]

    results = []
    for i in top_ids:
        item = dict(chunks[int(i)])
        item["score"] = float(scores[i])
        results.append(item)
    return results


def search_many(questions, index, chunks, k=5):
    """Like search(), but for many questions at once.

    Used by the Evaluation tab. The questions are sent to Gemini in batches,
    which is much faster and cheaper than one request per question.
    Returns one list of results per question.
    """
    if not questions:
        return []

    parts = []
    for start in range(0, len(questions), BATCH_SIZE):
        parts.append(_embed(questions[start:start + BATCH_SIZE], "RETRIEVAL_QUERY"))
    q_matrix = _normalise(np.vstack(parts))
    all_scores = q_matrix @ index.T          # one row of scores per question

    k = min(k, len(chunks))
    output = []
    for scores in all_scores:
        top_ids = np.argsort(scores)[::-1][:k]
        results = []
        for i in top_ids:
            item = dict(chunks[int(i)])
            item["score"] = float(scores[i])
            results.append(item)
        output.append(results)
    return output