"""app.py - Stage 5: the Streamlit website.

Run with:  streamlit run app.py
"""

import streamlit as st

from ingest import load_file, chunk_pages
from retrieval import build_index, search
from llm import ask_llm, NOT_FOUND_MESSAGE

st.set_page_config(page_title="Smart Document Assistant", page_icon="📚", layout="wide")
st.title("📚 Smart Document Knowledge Assistant")
st.caption("Upload your notes, then ask questions. Answers come only from your files.")

# ---- Memory that survives Streamlit's re-runs -------------------------------
# Streamlit re-runs this whole file on every click, so anything we want to keep
# must live in st.session_state.
if "messages" not in st.session_state:
    st.session_state.messages = []      # the chat history
if "chunks" not in st.session_state:
    st.session_state.chunks = []        # all chunks from the uploaded files
if "index" not in st.session_state:
    st.session_state.index = None       # the FAISS search index
if "file_names" not in st.session_state:
    st.session_state.file_names = []


def show_sources(sources):
    """Expandable box listing the exact snippets used for an answer."""
    with st.expander(f"Sources ({len(sources)})"):
        for s in sources:
            st.markdown(
                f"**{s['source']}, page {s['page']}**  (similarity {s['score']:.2f})"
            )
            st.text(s["text"])
            st.divider()


# ---- Sidebar: upload + settings ---------------------------------------------
with st.sidebar:
    st.header("1. Upload documents")
    files = st.file_uploader(
        "PDF or TXT files", type=["pdf", "txt"], accept_multiple_files=True
    )

    if st.button("Process documents", type="primary"):
        if not files:
            st.warning("Choose at least one file first.")
        else:
            with st.spinner("Reading and indexing your documents..."):
                pages = []
                for f in files:
                    pages.extend(load_file(f))
                chunks = chunk_pages(pages)

                if not chunks:
                    st.error(
                        "No text found. Scanned PDFs are images, so they can't be read."
                    )
                else:
                    st.session_state.chunks = chunks
                    st.session_state.index = build_index(chunks)
                    st.session_state.file_names = [f.name for f in files]
                    st.session_state.messages = []  # fresh chat for new documents

    if st.session_state.file_names:
        st.success(
            f"Ready: {len(st.session_state.chunks)} chunks "
            f"from {len(st.session_state.file_names)} file(s)"
        )

    st.header("2. Settings")
    top_k = st.slider("Chunks to retrieve", 3, 5, 4)
    threshold = st.slider(
        "Relevance threshold",
        0.0, 1.0, 0.30, 0.05,
        help="If the best match scores below this, the app says the answer "
             "isn't in your documents instead of guessing.",
    )
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ---- Show the chat so far ---------------------------------------------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            show_sources(m["sources"])

# ---- Handle a new question --------------------------------------------------
question = st.chat_input("Ask a question about your documents")

if question:
    if st.session_state.index is None:
        st.warning("Upload and process your documents first (left sidebar).")
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching your documents..."):
                results = search(
                    question,
                    st.session_state.index,
                    st.session_state.chunks,
                    k=top_k,
                )
                if not results or results[0]["score"] < threshold:
                    answer = NOT_FOUND_MESSAGE
                    sources = []
                else:
                    answer = ask_llm(question, results)
                    sources = results

            st.markdown(answer)
            if sources:
                show_sources(sources)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )
