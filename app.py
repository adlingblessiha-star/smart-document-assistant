"""app.py - the Streamlit website, restyled.

Run with:  streamlit run app.py
"""

from collections import Counter

import streamlit as st

from ingest import load_file, chunk_pages
from retrieval import build_index, search
from llm import ask_llm, rewrite_question, NOT_FOUND_MESSAGE
from eval_ui import render_evaluation
from ui import (
    CSS,
    hero_html,
    steps_html,
    ready_html,
    pills_html,
    files_html,
    source_card_html,
)

st.set_page_config(page_title="Smart Document Assistant", page_icon="📚", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

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
if "pages" not in st.session_state:
    st.session_state.pages = []         # raw pages, kept for the chunk-size test
if "eval_results" not in st.session_state:
    st.session_state.eval_results = None
if "eval_sweep" not in st.session_state:
    st.session_state.eval_sweep = None

USER_AVATAR = "🧑‍🎓"
BOT_AVATAR = "📘"


def show_sources(sources, query=None):
    """Expandable box with one margin-note card per passage used."""
    with st.expander(f"Sources ({len(sources)} passages)"):
        cards = "".join(source_card_html(s, query) for s in sources)
        st.markdown(cards, unsafe_allow_html=True)


def render_message(role, content):
    """Draw one message. Special replies get their own look."""
    if role == "assistant" and content == NOT_FOUND_MESSAGE:
        st.info(
            "This isn't in your documents. Try rephrasing, or upload the file "
            "that covers it.",
            icon="📭",
        )
    elif role == "assistant" and content.startswith("Sorry,"):
        st.warning(content)
    else:
        st.markdown(content)


# ---- Sidebar: upload, status, settings --------------------------------------
with st.sidebar:
    st.markdown('<div class="side-title">Your documents</div>', unsafe_allow_html=True)
    files = st.file_uploader(
        "Add PDF or TXT files",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button("Process documents", type="primary", width="stretch"):
        if not files:
            st.warning("Add at least one file first.")
        else:
            with st.status("Processing documents", expanded=True) as status:
                st.write("Reading files...")
                pages = []
                for f in files:
                    pages.extend(load_file(f))
                chunks = chunk_pages(pages)

                if not chunks:
                    status.update(label="No readable text found", state="error")
                    st.error(
                        "Scanned PDFs are images, so their text can't be read. "
                        "Try a PDF where you can select the text."
                    )
                else:
                    st.write(
                        f"Split into {len(chunks)} passages. Creating embeddings "
                        "with Gemini..."
                    )
                    bar = st.progress(0.0)
                    try:
                        index = build_index(
                            chunks,
                            progress=lambda done, total: bar.progress(done / total),
                        )
                    except Exception as e:
                        status.update(label="Could not build the index", state="error")
                        st.error(
                            f"{e}\n\nCheck your internet connection and your "
                            "GEMINI_API_KEY, then try again."
                        )
                    else:
                        st.session_state.chunks = chunks
                        st.session_state.pages = pages
                        st.session_state.index = index
                        st.session_state.eval_results = None
                        st.session_state.eval_sweep = None
                        st.session_state.file_names = [f.name for f in files]
                        st.session_state.messages = []  # fresh chat for new documents
                        status.update(
                            label="Ready to answer questions",
                            state="complete",
                            expanded=False,
                        )

    if st.session_state.chunks:
        counts = Counter(c["source"] for c in st.session_state.chunks)
        st.markdown(files_html(counts), unsafe_allow_html=True)

    st.write("")
    with st.expander("Search settings"):
        top_k = st.slider("Passages to retrieve", 3, 5, 4)
        threshold = st.slider(
            "Relevance threshold",
            0.0, 1.0, 0.55, 0.05,
            help="If the best match scores below this, the app says the answer "
                 "isn't in your documents instead of guessing.",
        )
        use_rewrite = st.checkbox(
            "Understand follow-up questions",
            value=True,
            help="Rewrites questions like 'what about its units?' into full "
                 "questions using the chat history before searching.",
        )

    if st.button("Clear chat", width="stretch"):
        st.session_state.messages = []
        st.rerun()

# ---- Header -----------------------------------------------------------------
ready = st.session_state.index is not None

st.markdown(hero_html(), unsafe_allow_html=True)
if ready:
    st.markdown(
        pills_html(len(st.session_state.file_names), len(st.session_state.chunks)),
        unsafe_allow_html=True,
    )

# ---- Chat / Evaluation switch -----------------------------------------------
CHAT_VIEW = "💬 Chat"
EVAL_VIEW = "📊 Evaluation"
view = st.radio(
    "View", [CHAT_VIEW, EVAL_VIEW], horizontal=True, label_visibility="collapsed"
)

if view == EVAL_VIEW:
    if ready:
        render_evaluation(threshold)
    else:
        st.markdown(steps_html(), unsafe_allow_html=True)
    st.stop()  # nothing below (the chat) is drawn on this view

# ---- Question box -----------------------------------------------------------
# Streamlit always pins the chat box to the bottom, wherever we call it.
question = st.chat_input(
    "Ask a question about your notes" if ready else "Add and process your notes first",
    disabled=not ready,
)

# ---- Empty states -----------------------------------------------------------
if not st.session_state.messages and not question:
    st.markdown(ready_html() if ready else steps_html(), unsafe_allow_html=True)

# ---- Show the chat so far ---------------------------------------------------
for m in st.session_state.messages:
    avatar = USER_AVATAR if m["role"] == "user" else BOT_AVATAR
    with st.chat_message(m["role"], avatar=avatar):
        if m.get("rewritten"):
            st.caption(f"🔎 Searched for: {m['rewritten']}")
        render_message(m["role"], m["content"])
        if m.get("sources"):
            show_sources(m["sources"], m.get("query"))

# ---- Handle a new question --------------------------------------------------
if question and ready:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(question)

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Searching your documents..."):
            # Turn follow-ups ("what about its units?") into full questions.
            # [:-1] leaves out the question we just added to the history.
            search_query = question
            if use_rewrite:
                search_query = rewrite_question(
                    question, st.session_state.messages[:-1]
                )
            rewritten = search_query if search_query != question else None

            try:
                results = search(
                    search_query,
                    st.session_state.index,
                    st.session_state.chunks,
                    k=top_k,
                )
                search_error = None
            except Exception as e:
                results, search_error = [], e

            if search_error:
                answer = (
                    f"Sorry, the search step failed ({search_error}). "
                    "Check your internet connection and try again."
                )
                sources = []
            elif not results or results[0]["score"] < threshold:
                answer = NOT_FOUND_MESSAGE
                sources = []
            else:
                answer = ask_llm(search_query, results)
                sources = results

        if rewritten:
            st.caption(f"🔎 Searched for: {rewritten}")
        render_message("assistant", answer)
        if sources:
            show_sources(sources, search_query)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "rewritten": rewritten,
            "query": search_query,
        }
    )