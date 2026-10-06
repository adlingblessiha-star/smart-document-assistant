"""eval_ui.py - the Evaluation view (called from app.py).

Flow on screen:
  1. Write test questions (or let Gemini suggest some) in an editable table.
  2. Run the evaluation and see how often the search finds the right passage.
  3. Optionally compare chunk sizes to justify the one you use.
"""

import os
import random

import pandas as pd
import streamlit as st

from evaluate import run_evaluation, compare_chunk_sizes
from ingest import chunk_pages
from llm import generate_questions

EVAL_FILE = "eval_set.csv"
COLUMNS = ["Question", "File", "Page", "Phrase", "In notes?"]


# ---- Test-set table helpers -------------------------------------------------

def _clean_df(df):
    """Make sure the table has the right columns and types."""
    df = df.copy()
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS]
    df["Question"] = df["Question"].astype("object")
    df["File"] = df["File"].astype("object")
    df["Page"] = pd.to_numeric(df["Page"], errors="coerce").astype("Int64")
    df["Phrase"] = df["Phrase"].astype("object")
    df["In notes?"] = df["In notes?"].fillna(True).astype(bool)
    return df.reset_index(drop=True)


def _empty_df():
    return _clean_df(pd.DataFrame(columns=COLUMNS))


def _load_saved():
    if os.path.exists(EVAL_FILE):
        try:
            return _clean_df(pd.read_csv(EVAL_FILE))
        except Exception:
            pass
    return _empty_df()


def _cases_from_df(df):
    """Turn table rows into test cases for evaluate.py. Blank rows are skipped."""
    cases = []
    for _, r in df.iterrows():
        question = str(r["Question"]).strip() if pd.notna(r["Question"]) else ""
        if not question or question.lower() == "nan":
            continue
        in_notes = bool(r["In notes?"]) if pd.notna(r["In notes?"]) else True
        file = str(r["File"]).strip() if pd.notna(r["File"]) else ""
        phrase = str(r["Phrase"]).strip() if pd.notna(r["Phrase"]) else ""
        cases.append(
            {
                "question": question,
                "in_notes": in_notes,
                "file": file or None,
                "page": int(r["Page"]) if pd.notna(r["Page"]) else None,
                "phrase": phrase or None,
            }
        )
    return cases


def _sample_chunks(chunks, n):
    """Pick up to n passages, preferring different pages."""
    shuffled = chunks[:]
    random.shuffle(shuffled)
    picked, seen_pages = [], set()
    for c in shuffled:
        key = (c["source"], c["page"])
        if key not in seen_pages:
            picked.append(c)
            seen_pages.add(key)
        if len(picked) == n:
            return picked
    for c in shuffled:
        if len(picked) == n:
            break
        if c not in picked:
            picked.append(c)
    return picked


def _pct(count, total):
    return f"{100 * count / total:.0f}%" if total else "n/a"


# ---- Results display --------------------------------------------------------

def _show_results(res, threshold):
    s = res["summary"]
    st.markdown("#### Results")

    if s["n_pos"]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Top 1 ({s['hit1']} of {s['n_pos']})", _pct(s["hit1"], s["n_pos"]))
        c2.metric(f"Top 3 ({s['hit3']} of {s['n_pos']})", _pct(s["hit3"], s["n_pos"]))
        c3.metric(f"Top 5 ({s['hit5']} of {s['n_pos']})", _pct(s["hit5"], s["n_pos"]))
        c4.metric("Average rank score", f"{s['mrr']:.2f}")
        st.caption(
            "Top 3 means the right passage was among the 3 best matches. "
            "Average rank score is 1.00 if the right passage is always first, "
            "0.50 if it is typically second."
        )
        st.bar_chart(
            pd.DataFrame(
                {"Found (%)": [
                    100 * s["hit1"] / s["n_pos"],
                    100 * s["hit3"] / s["n_pos"],
                    100 * s["hit5"] / s["n_pos"],
                ]},
                index=["Top 1", "Top 3", "Top 5"],
            )
        )

    c5, c6 = st.columns(2)
    if s["n_neg"]:
        c5.metric(
            f"Correctly refused ({s['refused_ok']} of {s['n_neg']})",
            _pct(s["refused_ok"], s["n_neg"]),
            help=f"Questions marked 'not in notes' whose best score was below "
                 f"the threshold ({threshold:.2f}).",
        )
    if s["n_pos"]:
        c6.metric(
            f"Wrongly refused ({s['wrongly_refused']} of {s['n_pos']})",
            _pct(s["wrongly_refused"], s["n_pos"]),
            help="Questions that ARE in your notes, but whose best score was "
                 "below the threshold, so the app would say 'not in your documents'.",
        )

    # One row per question
    table = []
    for r in res["rows"]:
        if r["in_notes"]:
            rank = r["rank"]
            icon = "✅" if rank == 1 else ("🟡" if rank else "❌")
            note = "would be refused" if r["would_refuse"] else ""
            found_at = str(rank) if rank else "not in top 5"
        else:
            icon = "✅" if r["refused"] else "❌"
            note = "refused" if r["refused"] else "answered anyway"
            found_at = "-"
        top = r["retrieved"][0] if r["retrieved"] else None
        table.append(
            {
                "": icon,
                "Question": r["question"],
                "Expected": r["expected"],
                "Found at": found_at,
                "Best score": round(r["top_score"], 2),
                "Top result": f"{top['source']}, p. {top['page']}" if top else "-",
                "Note": note,
            }
        )
    st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)
    st.caption("✅ first place (or correctly refused)   🟡 found in top 5   ❌ missed")

    misses = [r for r in res["rows"] if r["in_notes"] and r["rank"] is None]
    if misses:
        with st.expander(f"Why did {len(misses)} question(s) miss?"):
            for r in misses:
                st.markdown(f"**{r['question']}**  \nExpected: {r['expected']}")
                for chunk in r["retrieved"][:2]:
                    st.caption(
                        f"Found instead: {chunk['source']}, p. {chunk['page']} "
                        f"(score {chunk['score']:.2f})"
                    )
                    st.text(chunk["text"][:300])
                st.divider()


def _show_sweep(rows):
    st.markdown("#### Chunk size results")
    table = pd.DataFrame(
        [
            {
                "Chunk size": r["size"],
                "Passages": r["passages"],
                "Top 1": _pct(r["hit1"], r["n_pos"]),
                "Top 3": _pct(r["hit3"], r["n_pos"]),
                "Average rank score": round(r["mrr"], 2),
            }
            for r in rows
        ]
    )
    st.dataframe(table, width="stretch", hide_index=True)

    chart = pd.DataFrame(
        {
            "Top 3 (%)": [100 * r["hit3"] / r["n_pos"] if r["n_pos"] else 0 for r in rows],
            "Top 1 (%)": [100 * r["hit1"] / r["n_pos"] if r["n_pos"] else 0 for r in rows],
        },
        index=[f"{r['size']} chars" for r in rows],
    )
    st.bar_chart(chart)

    best = max(rows, key=lambda r: (r["hit3"], r["hit1"], r["mrr"]))
    st.info(
        f"Best on your test questions: **{best['size']} characters**. "
        "To use it, change `size=800` (and `overlap=150`) in `chunk_pages` and "
        "`chunk_text` in `ingest.py`, then process your documents again."
    )


# ---- The view ---------------------------------------------------------------

def render_evaluation(threshold):
    chunks = st.session_state.chunks
    pages = st.session_state.get("pages", [])
    index = st.session_state.index
    file_names = sorted({c["source"] for c in chunks})

    if "eval_df" not in st.session_state:
        st.session_state.eval_df = _load_saved()
        st.session_state.eval_version = 0

    st.subheader("Measure how well the search works")
    st.write(
        "Write questions whose answers you know, tell the app where the answer "
        "lives, and it checks whether the search finds that passage. Aim for "
        "10 to 15 questions, and write some in your own words rather than "
        "copying your notes."
    )

    # 1. Test questions ------------------------------------------------------
    st.markdown("##### 1. Your test questions")
    st.caption(
        "**File, Page and Phrase** say where the right answer is. Fill in at "
        "least one. Phrase is a word or short phrase that must appear in the "
        "right passage, which is handy for text files with only one page. "
        "Untick **In notes?** for questions that are NOT in your documents, to "
        "test the refusal."
    )

    edited = st.data_editor(
        st.session_state.eval_df,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key=f"eval_editor_{st.session_state.eval_version}",
        column_config={
            "Question": st.column_config.TextColumn("Question", width="large"),
            "File": st.column_config.SelectboxColumn("File", options=file_names),
            "Page": st.column_config.NumberColumn("Page", min_value=1, step=1),
            "Phrase": st.column_config.TextColumn(
                "Phrase", help="Optional: must appear in the right passage"
            ),
            "In notes?": st.column_config.CheckboxColumn("In notes?", default=True),
        },
    )

    b1, b2, b3 = st.columns(3)
    if b1.button(
        "Suggest 8 questions",
        width="stretch",
        help="Gemini writes draft questions from random passages of your notes. "
             "Read them and edit them, since they are easier than real questions.",
    ):
        with st.spinner("Writing questions from your notes..."):
            new_rows = generate_questions(_sample_chunks(chunks, 8))
        if new_rows:
            st.session_state.eval_df = _clean_df(
                pd.concat([edited, pd.DataFrame(new_rows)], ignore_index=True)
            )
            st.session_state.eval_version += 1
            st.rerun()
        else:
            st.warning("Could not get suggestions right now. Try again in a minute.")

    if b2.button("Save test set", width="stretch"):
        _clean_df(edited).to_csv(EVAL_FILE, index=False)
        st.success(f"Saved to {EVAL_FILE} in your project folder.")

    if b3.button("Clear table", width="stretch"):
        st.session_state.eval_df = _empty_df()
        st.session_state.eval_version += 1
        st.session_state.eval_results = None
        st.rerun()

    cases = _cases_from_df(edited)
    n_pos = sum(1 for c in cases if c["in_notes"])
    n_neg = len(cases) - n_pos
    st.caption(
        f"{n_pos} question(s) that should be found, {n_neg} that should be refused."
        + ("  Aim for 10 or more found-questions for numbers worth quoting." if n_pos < 10 else "")
    )

    # 2. Run -----------------------------------------------------------------
    st.markdown("##### 2. Run the evaluation")
    if st.button("Run evaluation", type="primary", disabled=not cases):
        with st.spinner("Searching with every question..."):
            try:
                st.session_state.eval_results = run_evaluation(
                    cases, index, chunks, threshold
                )
            except Exception as e:
                st.session_state.eval_results = None
                st.error(f"Evaluation failed: {e}")

    if st.session_state.get("eval_results"):
        _show_results(st.session_state.eval_results, threshold)
        st.caption("These results are from your last run. Run again after editing.")

    # 3. Chunk sizes ---------------------------------------------------------
    st.markdown("##### 3. Compare chunk sizes (optional)")
    st.write(
        "Splits your documents at different sizes and scores the same questions "
        "each time, so you can justify the chunk size you use."
    )
    sizes = st.multiselect(
        "Chunk sizes to try (characters)",
        [300, 500, 800, 1200, 1600],
        default=[500, 800, 1200],
    )
    total_passages = sum(
        len(chunk_pages(pages, size=sz, overlap=sz * 3 // 16)) for sz in sizes
    ) if pages else 0
    if sizes:
        st.caption(
            f"This re-embeds your documents once per size: about {total_passages} "
            "passages in total, which uses your free API quota. Use a short "
            "document while testing."
        )

    if st.button("Compare chunk sizes", disabled=not (cases and sizes and pages)):
        with st.status("Comparing chunk sizes", expanded=True) as status:
            bar = st.progress(0.0)
            label = st.empty()

            def on_progress(n, total_sizes, size, done, total):
                label.write(f"Size {size}: embedding passages ({n + 1} of {total_sizes})")
                bar.progress(min(1.0, (n + done / total) / total_sizes))

            try:
                st.session_state.eval_sweep = compare_chunk_sizes(
                    pages, cases, sorted(sizes), threshold, progress=on_progress
                )
                status.update(label="Done", state="complete", expanded=False)
            except Exception as e:
                st.session_state.eval_sweep = None
                status.update(label="Comparison failed", state="error")
                st.error(str(e))

    if st.session_state.get("eval_sweep"):
        _show_sweep(st.session_state.eval_sweep)
