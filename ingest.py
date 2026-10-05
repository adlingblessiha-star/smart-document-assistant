"""ingest.py - Stages 1 and 2: read uploaded files and split them into chunks.

Every chunk keeps its source file and page number, so we can cite it later:
    {"source": "lab_manual.pdf", "page": 12, "text": "..."}
"""

import fitz  # PyMuPDF


def load_file(uploaded_file):
    """Read one uploaded file (PDF or TXT). Returns a list of page dicts."""
    name = uploaded_file.name
    data = uploaded_file.getvalue()
    pages = []

    if name.lower().endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:  # scanned/image-only pages give empty text, so skip them
                pages.append({"source": name, "page": i + 1, "text": text})
    else:
        text = data.decode("utf-8", errors="ignore").strip()
        if text:
            pages.append({"source": name, "page": 1, "text": text})

    return pages


def chunk_text(text, size=800, overlap=150):
    """Cut text into pieces of about `size` characters that overlap a little."""
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def chunk_pages(pages, size=800, overlap=150):
    """Turn page dicts into chunk dicts, keeping source and page number."""
    chunks = []
    for p in pages:
        for piece in chunk_text(p["text"], size, overlap):
            if piece.strip():
                chunks.append(
                    {"source": p["source"], "page": p["page"], "text": piece}
                )
    return chunks