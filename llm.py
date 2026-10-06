"""llm.py - talks to Gemini.

Two jobs:
  1. rewrite_question(): turn a follow-up like "what about its units?" into a
     full standalone question, using the chat history (so search works).
  2. ask_llm(): answer a question using ONLY the retrieved chunks.

Each chunk is a dict like:
    {"source": "lab_manual.pdf", "page": 12, "text": "..."}
"""

import os
import re
import time
from dotenv import load_dotenv
from google import genai

# Reads GEMINI_API_KEY from your .env file
load_dotenv()

# If you get a "model not found" error, run `python llm.py models`
# to list the names your key can use, then paste one here.
# (Google's own error message also names the replacement model.)
MODEL_NAME = "gemini-3.8-flash"

# If MODEL_NAME is ever "not found" (Google retires models regularly), these are
# tried next. The one that works is remembered for the rest of the session.
FALLBACK_MODELS = ["gemini-2.5-flash"]
_working_model = None

NOT_FOUND_MESSAGE = "This isn't in your documents."

# Seconds to wait before each retry when Gemini is busy (3 retries in total)
RETRY_DELAYS = [2, 5, 10]

_client = None


def get_client():
    """Create the Gemini client once and reuse it."""
    global _client
    if _client is None:
        # Locally the key comes from your .env file. When deployed on Streamlit
        # Community Cloud it comes from the app's Secrets settings.
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                api_key = None
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not found. Locally, check that your .env file is "
                "in the project folder and contains: GEMINI_API_KEY=your_key. "
                "On Streamlit Cloud, add it under the app's Settings, Secrets."
            )
        api_key = str(api_key).strip()
        _client = genai.Client(api_key=api_key)
    return _client


def _model_order():
    """Models to try, with the last one that worked first."""
    order = [MODEL_NAME] + [m for m in FALLBACK_MODELS if m != MODEL_NAME]
    if _working_model in order:
        order.remove(_working_model)
        order.insert(0, _working_model)
    return order


def _generate(prompt):
    """Send a prompt to Gemini. Returns (text, error); exactly one is None.

    - Temporary errors (503 busy, 429 rate limit) are retried a few times.
    - A 404 "model not found" moves on to the next model in FALLBACK_MODELS.
    """
    global _working_model
    last_error = None

    for model in _model_order():
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                response = get_client().models.generate_content(
                    model=model,
                    contents=prompt,
                )
                _working_model = model
                if response.text:
                    return response.text.strip(), None
                return None, "The model returned an empty answer."
            except Exception as e:
                last_error = e
                message = str(e)
                if "404" in message or "NOT_FOUND" in message:
                    break  # this model name isn't available, try the next one
                is_temporary = any(
                    word in message
                    for word in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
                )
                if is_temporary and attempt < len(RETRY_DELAYS):
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                return None, last_error

    return None, last_error


# ---------------------------------------------------------------------------
# Follow-up rewriting
# ---------------------------------------------------------------------------

def build_rewrite_prompt(question, history):
    """Show the recent chat and ask for a standalone version of the question."""
    lines = []
    for m in history[-6:]:  # only the last few messages are needed
        who = "Student" if m["role"] == "user" else "Assistant"
        text = m["content"]
        if len(text) > 400:
            text = text[:400] + "..."
        lines.append(f"{who}: {text}")
    chat = "\n".join(lines)

    return f"""Below is a conversation between a student and a study assistant,
followed by the student's new message.

Rewrite the new message as ONE complete, standalone question that makes sense
without the conversation. Replace words like "it", "that", "its", "they" and
"this" with what they refer to.

Rules:
- If the new message is already clear on its own, return it unchanged.
- Do not answer the question.
- Do not add any information that is not in the conversation.
- Output ONLY the rewritten question, nothing else.

Conversation:
{chat}

New message: {question}

Standalone question:"""


def rewrite_question(question, history):
    """Return a standalone version of `question`.

    If there is no chat history, or anything goes wrong, the original question
    is returned, so rewriting can never break the app.
    """
    if not history:
        return question

    text, error = _generate(build_rewrite_prompt(question, history))
    if error or not text:
        return question

    text = text.strip().strip('"').strip()
    # Safety check: reject empty or absurdly long rewrites
    if not text or len(text) > 400:
        return question
    return text


# ---------------------------------------------------------------------------
# Answering
# ---------------------------------------------------------------------------

def build_prompt(question, chunks):
    """Put the retrieved chunks and the question into one grounded prompt."""
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"[Source {i}: {chunk['source']}, page {chunk['page']}]\n{chunk['text']}"
        )
    context = "\n\n".join(context_parts)

    return f"""You are a study assistant for first-year students.
Answer the question using ONLY the context below.

Rules:
- Do not use any outside knowledge.
- If the context does not contain the answer, reply exactly: "{NOT_FOUND_MESSAGE}"
- Mention the source file and page number for each fact, like (lab_manual.pdf, p. 12).
- Keep the answer clear and short.

Context:
{context}

Question: {question}

Answer:"""


def ask_llm(question, chunks):
    """Return the model's answer as a string."""
    text, error = _generate(build_prompt(question, chunks))
    if text:
        return text
    return (
        "Sorry, the AI service is busy or unavailable right now. "
        f"Please try again in a minute. (Details: {error})"
    )


# ---------------------------------------------------------------------------
# Test-question suggestions (used by the Evaluation tab)
# ---------------------------------------------------------------------------

def generate_questions(chunks):
    """Ask Gemini for one test question per passage.

    Returns a list of rows ready for the Evaluation table:
        {"Question", "File", "Page", "Phrase", "In notes?"}
    Phrase is a short piece of text the right passage must contain. It is only
    kept if it really appears in that passage.
    """
    blocks = [f"[{i}]\n{c['text']}" for i, c in enumerate(chunks, start=1)]
    passages = "\n\n".join(blocks)

    prompt = f"""You are helping test a search system that looks things up in student notes.
For EACH numbered passage below, write ONE question a student could answer using
only that passage. Also give a key phrase (1 to 4 words) copied exactly from the
passage that the answer depends on.

Rules:
- Use your own wording. Do not copy whole sentences from the passage.
- The question must make sense on its own (never say "in this passage").
- Output exactly one line per passage, in this format:
  number | question | key phrase
- Output nothing else.

Passages:
{passages}
"""
    text, error = _generate(prompt)
    if error or not text:
        return []

    rows = []
    for line in text.splitlines():
        cells = [p.strip() for p in line.split("|")]
        if len(cells) < 2:
            continue
        match = re.match(r"\[?(\d+)\]?", cells[0])
        if not match:
            continue
        idx = int(match.group(1)) - 1
        if not 0 <= idx < len(chunks) or not cells[1]:
            continue

        chunk = chunks[idx]
        phrase = cells[2] if len(cells) > 2 else ""
        if phrase.lower() not in chunk["text"].lower():
            phrase = ""
        rows.append(
            {
                "Question": cells[1],
                "File": chunk["source"],
                "Page": int(chunk["page"]),
                "Phrase": phrase,
                "In notes?": True,
            }
        )
    return rows


def list_models():
    """Print the model names available to your API key."""
    for m in get_client().models.list():
        print(m.name)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "models":
        list_models()
        sys.exit()

    test_chunks = [
        {
            "source": "physics_notes.pdf",
            "page": 3,
            "text": "Ohm's law states that the current through a conductor is "
                    "directly proportional to the voltage across it, provided "
                    "the temperature stays constant. V = I x R.",
        },
        {
            "source": "physics_notes.pdf",
            "page": 4,
            "text": "Resistance depends on the length, cross-sectional area and "
                    "material of the conductor.",
        },
    ]

    print("TEST 1 (answer is in the context):")
    print(ask_llm("What is Ohm's law?", test_chunks))

    print("\nTEST 2 (answer is NOT in the context):")
    print(ask_llm("Who won the 2011 cricket world cup?", test_chunks))

    print("\nTEST 3 (follow-up rewriting):")
    fake_history = [
        {"role": "user", "content": "What is Ohm's law?"},
        {"role": "assistant", "content": "Ohm's law says V = I x R (physics_notes.pdf, p. 3)."},
    ]
    print(rewrite_question("What does R stand for in it?", fake_history))