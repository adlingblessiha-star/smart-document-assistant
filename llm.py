"""llm.py - Stage 4: send retrieved chunks + question to Gemini and get a grounded answer.

Each chunk is a dict like:
    {"source": "lab_manual.pdf", "page": 12, "text": "..."}
"""

import os
import time
from dotenv import load_dotenv
from google import genai

# Reads GEMINI_API_KEY from your .env file
load_dotenv()

# If you get a "model not found" error, run `python llm.py models`
# to list the names your key can use, then paste one here.
MODEL_NAME = "gemini-3.5-flash"

NOT_FOUND_MESSAGE = "This isn't in your documents."

# Seconds to wait before each retry when Gemini is busy (3 retries in total)
RETRY_DELAYS = [2, 5, 10]

_client = None


def get_client():
    """Create the Gemini client once and reuse it."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not found. Check that your .env file is in the "
                "doc-assistant folder and contains: GEMINI_API_KEY=your_key"
            )
        _client = genai.Client(api_key=api_key)
    return _client


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
    """Return the model's answer as a string.

    Gemini sometimes returns temporary errors (503 = busy, 429 = rate limit),
    so we retry a few times, waiting a bit longer each time.
    """
    prompt = build_prompt(question, chunks)
    last_error = None

    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            response = get_client().models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            return response.text or "The model returned an empty answer. Please try again."
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

    return (
        "Sorry, the AI service is busy or unavailable right now. "
        f"Please try again in a minute. (Details: {last_error})"
    )


def list_models():
    """Print the model names available to your API key."""
    for m in get_client().models.list():
        print(m.name)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "models":
        list_models()
        sys.exit()

    # Quick test with fake chunks (no PDF or search needed yet)
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