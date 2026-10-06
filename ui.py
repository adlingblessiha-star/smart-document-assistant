"""ui.py - all the visual styling and small HTML pieces for the app.

Design idea: a notebook on a desk. A ruled page with a red margin line and
punched holes, a yellow highlighter, and little doodles down the right edge.
Your question is highlighted, the words that matched are highlighted in the
source passages, and each passage carries a red page tag like a margin note.

To change the look, edit the colours in the :root block of CSS below.
To remove the doodles, delete the `.block-container::after` rule.
"""

import html
import re
from urllib.parse import quote


def _svg_uri(svg):
    """Turn an SVG string into a data: URI that CSS can use as an image."""
    return 'url("data:image/svg+xml,' + quote(svg.strip(), safe=" /:=',()-.") + '")'


_NAVY = "#1B2A4A"

DOODLE_STAR = _svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
    "<path d='M24 5 L29.5 18 L43 19 L32.5 28 L36 42 L24 34.5 L12 42 L15.5 28 "
    "L5 19 L18.5 18 Z' fill='#FFE066' stroke='#1B2A4A' stroke-width='2.4' "
    "stroke-linejoin='round'/></svg>"
)

DOODLE_SPARKLES = _svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none' "
    "stroke='#1B2A4A' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M14 4 Q15 13 24 14 Q15 15 14 24 Q13 15 4 14 Q13 13 14 4 Z' fill='#FFF4B8'/>"
    "<path d='M30 22 V34 M24 28 H36'/></svg>"
)

DOODLE_BULB = _svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 56 64' fill='none' "
    "stroke='#1B2A4A' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M28 8 C16 8 10 17 10 25 C10 32 15 36 18 41 C19 43 19 45 19 47 H37 "
    "C37 45 37 43 38 41 C41 36 46 32 46 25 C46 17 40 8 28 8 Z' fill='#FFF4B8'/>"
    "<path d='M23 31 L28 24 L33 31 M21 53 H35 M24 59 H32'/>"
    "<path d='M28 1 V3 M7 12 L9 14 M49 12 L47 14 M2 26 H5 M51 26 H54'/></svg>"
)

DOODLE_HEART = _svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 44 40'>"
    "<path d='M22 36 C8 26 3 18 4 12 C5 6 11 3 16 5 C19 6 21 9 22 11 C23 9 25 6 "
    "28 5 C33 3 39 6 40 12 C41 18 36 26 22 36 Z' fill='#FFD0D3' stroke='#D64550' "
    "stroke-width='2.4' stroke-linejoin='round'/></svg>"
)

DOODLE_FLOWER = _svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 52 70' stroke='#1B2A4A' "
    "stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M26 38 C26 50 24 58 26 68' fill='none'/>"
    "<path d='M26 54 C34 50 38 52 40 46 C34 44 28 47 26 54 Z' fill='#CDEFD8'/>"
    "<circle cx='26' cy='9' r='8' fill='#fff'/><circle cx='38' cy='18' r='8' fill='#fff'/>"
    "<circle cx='33' cy='32' r='8' fill='#fff'/><circle cx='19' cy='32' r='8' fill='#fff'/>"
    "<circle cx='14' cy='18' r='8' fill='#fff'/>"
    "<circle cx='26' cy='22' r='6' fill='#FFE066'/></svg>"
)

DOODLE_PENCIL = _svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' stroke='#1B2A4A' "
    "stroke-width='2.2' stroke-linejoin='round' stroke-linecap='round'>"
    "<path d='M10 54 L14 42 L44 12 L52 20 L22 50 Z' fill='#FFE066'/>"
    "<path d='M10 54 L14 42 L22 50 Z' fill='#F4D9B5'/>"
    "<path d='M44 12 L48 8 Q52 5 56 9 Q59 13 56 16 L52 20 Z' fill='#F8B4B9'/>"
    "<path d='M19 47 L49 17' fill='none' stroke-width='1.4'/></svg>"
)

DOODLE_SQUIGGLE = _svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' width='40' height='12' viewBox='0 0 40 12'>"
    "<path d='M0 6 Q10 -1 20 6 T40 6' fill='none' stroke='#FFE066' stroke-width='4.5' "
    "stroke-linecap='round'/></svg>"
)

_CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Caveat:wght@600;700&family=Figtree:wght@400;500;600&family=Newsreader:ital,wght@0,400;0,500;1,400&display=swap');

:root {
  --desk: #D9E3F2;
  --page: #FDFEFF;
  --ink: #1B2A4A;
  --ink-soft: rgba(27, 42, 74, 0.68);
  --highlighter: #FFE066;
  --highlighter-soft: #FFF4B8;
  --margin-red: #D64550;
  --rule: #D5DDEB;
  --card: #FFFFFF;
}

html, body, .stApp, [data-testid="stSidebar"] {
  font-family: 'Figtree', system-ui, -apple-system, 'Segoe UI', sans-serif;
  color: var(--ink);
}

/* The desk: pale blue with tiny dots */
.stApp {
  background-color: var(--desk);
  background-image: radial-gradient(rgba(27, 42, 74, 0.10) 1px, transparent 1.4px);
  background-size: 22px 22px;
  background-attachment: fixed;
}
header[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: transparent !important; }

/* The notebook page: ruled lines, red margin line, punched holes */
.block-container {
  position: relative;
  max-width: 940px !important;
  min-height: calc(100vh - 2.5rem);
  margin: 1rem auto 1.5rem !important;
  padding: 2.4rem 5rem 9rem 5.2rem !important;
  border-radius: 6px 16px 16px 6px;
  box-shadow: 0 12px 32px rgba(27, 42, 74, 0.16), 0 1px 0 rgba(27, 42, 74, 0.12);
  background-color: var(--page);
  background-image:
    radial-gradient(circle at 26px 110px,
      var(--desk) 0, var(--desk) 9px,
      rgba(27, 42, 74, 0.22) 9px, rgba(27, 42, 74, 0.22) 10px,
      transparent 10.5px),
    linear-gradient(90deg,
      transparent 62px, rgba(214, 69, 80, 0.55) 62px,
      rgba(214, 69, 80, 0.55) 64px, transparent 64px),
    repeating-linear-gradient(to bottom,
      transparent 0, transparent 31px,
      rgba(76, 129, 206, 0.22) 31px, rgba(76, 129, 206, 0.22) 32px);
  background-size: 100% 380px, 100% 100%, 100% 32px;
  background-repeat: repeat-y, no-repeat, repeat;
  background-position: 0 0, 0 0, 0 22px;
}

/* Doodles down the right edge of the page (decoration only) */
.block-container::after {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 92px;
  pointer-events: none;
  background-image: __STAR__, __SPARKLES__, __BULB__, __HEART__, __FLOWER__, __PENCIL__;
  background-repeat: no-repeat;
  background-size: 46px 46px, 30px 30px, 52px 60px, 38px 34px, 44px 60px, 56px 56px;
  background-position:
    24px 26px,
    44px 92px,
    20px 160px,
    28px 290px,
    24px 392px,
    22px calc(100% - 180px);
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: var(--card);
  border-right: 1px solid var(--rule);
}
.side-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 800;
  font-size: 1.25rem;
  letter-spacing: -0.01em;
  margin: 0.2rem 0 0.6rem;
}
.filerow {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--rule);
  font-size: 0.9rem;
}
.filerow .fname { font-weight: 600; overflow-wrap: anywhere; }
.filerow .fcount { color: var(--ink-soft); white-space: nowrap; }

/* Hero */
.hero { margin: 0 0 1.2rem; }
.hero h1 {
  font-family: 'Bricolage Grotesque', sans-serif !important;
  font-weight: 800 !important;
  font-size: 3.4rem !important;
  line-height: 1.02 !important;
  letter-spacing: -0.03em !important;
  margin: 0 0 0.2rem !important;
  padding: 0 !important;
  color: var(--ink) !important;
}
.squiggle {
  width: 200px;
  height: 12px;
  margin: 0 0 0.8rem;
  background-image: __SQUIGGLE__;
  background-repeat: repeat-x;
  background-size: 40px 12px;
}
.hero p {
  font-size: 1.08rem;
  line-height: 1.5;
  max-width: 34rem;
  margin: 0;
  color: var(--ink-soft);
}

/* Stat pills */
.pills { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0 0 1.4rem; }
.pill {
  background: var(--card);
  border: 1px solid var(--rule);
  border-radius: 999px;
  padding: 0.2rem 0.8rem;
  font-size: 0.88rem;
}
.pill b { font-weight: 600; }

/* Sticky note for the empty / ready states */
.empty {
  position: relative;
  background: var(--highlighter-soft);
  border-radius: 4px 4px 16px 4px;
  padding: 1.3rem 1.6rem 1.2rem;
  margin: 0.8rem 0 1.2rem;
  max-width: 30rem;
  transform: rotate(-1deg);
  box-shadow: 2px 5px 12px rgba(27, 42, 74, 0.16);
}
.empty::before {
  content: "";
  position: absolute;
  top: -11px;
  left: 50%;
  width: 92px;
  height: 22px;
  margin-left: -46px;
  background: rgba(214, 69, 80, 0.28);
  transform: rotate(2deg);
}
.empty h3 {
  font-family: 'Caveat', 'Bradley Hand', cursive;
  font-weight: 700;
  font-size: 1.9rem;
  line-height: 1.1;
  margin: 0 0 0.5rem;
  padding: 0;
}
.empty ol { margin: 0; padding-left: 1.3rem; line-height: 1.9; }
.empty p { margin: 0; line-height: 1.6; color: var(--ink); }

/* Chat messages */
[data-testid="stChatMessage"] {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--rule);
  border-radius: 14px;
  padding: 1rem 1.2rem;
}
/* Your questions get the highlighter */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--highlighter-soft);
  border-color: var(--highlighter);
}
[data-testid="stChatMessage"] p { line-height: 1.6; }
[data-testid="stCaptionContainer"] { color: var(--ink-soft); }
[data-testid="stExpander"] {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 10px;
}

/* Buttons */
.stButton > button {
  border-radius: 10px;
  border: 1px solid var(--rule);
  font-weight: 600;
}
.stButton > button:hover {
  border-color: var(--ink);
  background: var(--highlighter-soft);
  color: var(--ink);
}
.stButton > button[kind="primary"] {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}
.stButton > button[kind="primary"]:hover {
  background: #2A3E69;
  color: #fff;
}

/* Source passages: margin-note cards */
.src {
  background: var(--card);
  border: 1px solid var(--rule);
  border-left: 4px solid var(--margin-red);
  border-radius: 6px 12px 12px 6px;
  padding: 0.8rem 1rem 0.9rem;
  margin: 0.6rem 0;
}
.src-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  font-size: 0.88rem;
}
.src-page {
  background: var(--margin-red);
  color: #fff;
  font-weight: 600;
  border-radius: 999px;
  padding: 0.05rem 0.6rem;
}
.src-file { font-weight: 600; overflow-wrap: anywhere; }
.src-match { margin-left: auto; color: var(--ink-soft); }
.meter {
  height: 4px;
  background: var(--rule);
  border-radius: 4px;
  margin: 0.55rem 0 0.75rem;
}
.meter span {
  display: block;
  height: 100%;
  background: var(--ink);
  border-radius: 4px;
}
.src-text {
  font-family: 'Newsreader', Georgia, serif;
  font-size: 1.02rem;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
}
.src-text mark {
  background: linear-gradient(transparent 38%, var(--highlighter) 38%);
  color: inherit;
  padding: 0 0.1em;
}

/* Small screens: drop the doodle column and tighten the page */
@media (max-width: 900px) {
  .block-container {
    padding: 1.6rem 1rem 9rem 4.2rem !important;
    margin: 0.4rem 0.4rem 1rem !important;
  }
  .block-container::after { display: none; }
  .hero h1 { font-size: 2.4rem !important; }
}
</style>
"""

CSS = (
    _CSS_TEMPLATE
    .replace("__STAR__", DOODLE_STAR)
    .replace("__SPARKLES__", DOODLE_SPARKLES)
    .replace("__BULB__", DOODLE_BULB)
    .replace("__HEART__", DOODLE_HEART)
    .replace("__FLOWER__", DOODLE_FLOWER)
    .replace("__PENCIL__", DOODLE_PENCIL)
    .replace("__SQUIGGLE__", DOODLE_SQUIGGLE)
)

# Similarity cut-offs for the match labels. Check a few real scores in the
# source cards and adjust these two numbers if the labels feel off.
STRONG_MATCH = 0.72
GOOD_MATCH = 0.62

STOPWORDS = {
    "what", "which", "when", "where", "who", "whom", "whose", "why", "how",
    "does", "this", "that", "these", "those", "with", "from", "about", "into",
    "your", "have", "has", "had", "are", "was", "were", "the", "and", "for",
    "not", "can", "will", "would", "should", "could", "than", "then", "there",
    "their", "they", "them", "its", "explain", "tell", "give", "mean", "means",
}


def hero_html():
    return (
        '<div class="hero"><h1>Ask your notes</h1><div class="squiggle"></div>'
        "<p>Upload lecture PDFs or text files. Every answer comes only from "
        "your files, with the exact passages it used.</p></div>"
    )


def steps_html():
    return (
        '<div class="empty"><h3>Start with your notes</h3><ol>'
        "<li>Add PDF or TXT files in the sidebar.</li>"
        "<li>Press <b>Process documents</b>.</li>"
        "<li>Ask a question in the box below.</li>"
        "</ol></div>"
    )


def ready_html():
    return (
        '<div class="empty"><h3>Your notes are ready</h3>'
        "<p>Ask anything they cover. Follow-ups such as &ldquo;what about its "
        "units?&rdquo; work too. If the answer isn&rsquo;t in your files, the "
        "assistant will say so instead of guessing.</p></div>"
    )


def pills_html(n_files, n_chunks):
    files_word = "file" if n_files == 1 else "files"
    return (
        '<div class="pills">'
        f'<span class="pill"><b>{n_files}</b> {files_word}</span>'
        f'<span class="pill"><b>{n_chunks}</b> passages</span>'
        "</div>"
    )


def files_html(counts):
    """counts: dict of file name -> number of passages."""
    rows = []
    for name, n in counts.items():
        rows.append(
            '<div class="filerow">'
            f'<span class="fname">{html.escape(name)}</span>'
            f'<span class="fcount">{n} passages</span></div>'
        )
    return "".join(rows)


def match_label(score):
    if score >= STRONG_MATCH:
        return "Strong match"
    if score >= GOOD_MATCH:
        return "Good match"
    return "Weak match"


def highlight(text, query):
    """HTML-escape the text, then mark the words that appear in the query."""
    safe = html.escape(text, quote=False)
    words = {
        w.lower()
        for w in re.findall(r"[A-Za-z0-9]+", query or "")
        if len(w) > 3 and w.lower() not in STOPWORDS
    }
    if not words:
        return safe
    alternatives = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    pattern = re.compile(rf"\b(?:{alternatives})(?:s|es)?\b", re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", safe)


def source_card_html(source, query=None):
    score = max(0.0, min(1.0, source["score"]))
    return (
        '<div class="src"><div class="src-head">'
        f'<span class="src-page">p. {source["page"]}</span>'
        f'<span class="src-file">{html.escape(source["source"])}</span>'
        f'<span class="src-match">{match_label(score)}, similarity {score:.2f}</span>'
        "</div>"
        f'<div class="meter"><span style="width:{score * 100:.0f}%"></span></div>'
        f'<p class="src-text">{highlight(source["text"], query)}</p></div>'
    )