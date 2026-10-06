"""evaluate.py - measure how well the search finds the right passage.

A test case is a dict:
    {"question": "...", "in_notes": True,
     "file": "lab_manual.pdf" or None, "page": 12 or None, "phrase": "ohm" or None}

A retrieved passage counts as CORRECT when it matches every detail the test
case gives: the file, the page, and the phrase (the phrase must appear in the
passage text). Details left empty are not checked.

Questions marked in_notes=False should be REFUSED, meaning the best similarity
score is below the threshold. That tests the "not in your documents" feature.
"""

from ingest import chunk_pages
from retrieval import build_index, search_many


def is_correct(chunk, case):
    if case.get("file") and chunk["source"] != case["file"]:
        return False
    if case.get("page") and int(chunk["page"]) != int(case["page"]):
        return False
    if case.get("phrase") and case["phrase"].lower() not in chunk["text"].lower():
        return False
    return True


def describe(case):
    if not case["in_notes"]:
        return "Not in notes"
    parts = []
    if case.get("file"):
        parts.append(case["file"])
    if case.get("page"):
        parts.append(f"p. {case['page']}")
    if case.get("phrase"):
        parts.append(f"contains \u201c{case['phrase']}\u201d")
    return ", ".join(parts) if parts else "Any passage"


def run_evaluation(cases, index, chunks, threshold, k=5):
    """Run every test question through the search and score the results."""
    all_results = search_many([c["question"] for c in cases], index, chunks, k=k)

    rows = []
    for case, retrieved in zip(cases, all_results):
        top_score = retrieved[0]["score"] if retrieved else 0.0
        row = {
            "question": case["question"],
            "in_notes": case["in_notes"],
            "expected": describe(case),
            "top_score": top_score,
            "retrieved": retrieved,
        }
        if case["in_notes"]:
            rank = None
            for i, chunk in enumerate(retrieved, start=1):
                if is_correct(chunk, case):
                    rank = i
                    break
            row["rank"] = rank
            row["would_refuse"] = top_score < threshold
        else:
            row["refused"] = top_score < threshold
        rows.append(row)

    positives = [r for r in rows if r["in_notes"]]
    negatives = [r for r in rows if not r["in_notes"]]

    def hits(n):
        return sum(1 for r in positives if r["rank"] is not None and r["rank"] <= n)

    mrr = 0.0
    if positives:
        mrr = sum(1.0 / r["rank"] for r in positives if r["rank"]) / len(positives)

    summary = {
        "n_pos": len(positives),
        "n_neg": len(negatives),
        "hit1": hits(1),
        "hit3": hits(3),
        "hit5": hits(5),
        "mrr": mrr,
        "refused_ok": sum(1 for r in negatives if r["refused"]),
        "wrongly_refused": sum(1 for r in positives if r["would_refuse"]),
    }
    return {"rows": rows, "summary": summary}


def compare_chunk_sizes(pages, cases, sizes, threshold, progress=None):
    """Rebuild the index at each chunk size and score the same test questions.

    This re-embeds your documents once per size, so it uses API quota.
    progress(size_number, total_sizes, size, done, total) is called if given.
    """
    rows = []
    for n, size in enumerate(sizes):
        chunks = chunk_pages(pages, size=size, overlap=size * 3 // 16)

        def inner(done, total, n=n, size=size):
            if progress:
                progress(n, len(sizes), size, done, total)

        index = build_index(chunks, progress=inner)
        result = run_evaluation(cases, index, chunks, threshold)
        s = result["summary"]
        rows.append(
            {
                "size": size,
                "passages": len(chunks),
                "n_pos": s["n_pos"],
                "hit1": s["hit1"],
                "hit3": s["hit3"],
                "mrr": s["mrr"],
            }
        )
    return rows
