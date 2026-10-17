import json
import re
import time
from html import escape
from pathlib import Path

import streamlit as st
from generate import prepare, stream_tokens, finalize, no_evidence, MODEL

# ---------- settings you can change ----------
BOT_NAME = "DataSage"
EXAMPLES = [
    ("Explain overfitting", "What is overfitting?"),
    ("How PageRank works", "What is PageRank?"),
    ("Gradient descent, simply", "What is gradient descent?"),
    ("Compare two books", "Do Bishop and ISLR define the bias-variance tradeoff the same way?"),
]
# ---------------------------------------------

st.set_page_config(
    page_title=BOT_NAME,
    page_icon="📗",
    layout="centered",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_books():
    with open(Path("data/book_manifest.json"), encoding="utf-8") as f:
        return json.load(f)["books"]


def logo(size):
    """Vibrant green logo: an open book with a spark (pure SVG, no image file)."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        f'<rect width="64" height="64" rx="18" fill="#12C25B"/>'
        f'<path d="M12 22c6.5-3.2 13-3.2 19.5 1v24c-6.5-4.2-13-4.2-19.5-1z" fill="#FFFFFF"/>'
        f'<path d="M52 22c-6.5-3.2-13-3.2-19.5 1v24c6.5-4.2 13-4.2 19.5-1z" fill="#FFFFFF" opacity="0.85"/>'
        f'<path d="M17 29h9M17 34h9M38 29h9M38 34h9" stroke="#12C25B" stroke-width="2" stroke-linecap="round"/>'
        f'<circle cx="50" cy="12" r="3" fill="#FFFFFF"/>'
        f"</svg>"
    )


CSS = """
<style>
:root {
  --bg: #050605;
  --side: #0B0D0C;
  --card: #0E110F;
  --line: #1E2420;
  --text: #ECF1EE;
  --muted: #8D9791;
  --bubble: #171B19;
  --chip: #212724;
  --hover: #151916;
  --active: #1B201D;
  --brand: #12C25B;
  --brand-ink: #3DF58A;
  --font: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
}

.stApp {
  background:
    radial-gradient(1100px 520px at 50% -12%, rgba(18, 194, 91, 0.13), transparent 62%),
    var(--bg);
  color: var(--text);
}
.stApp p, .stApp li, .stApp label, .stApp textarea, .stApp input,
.stApp button p, .ds { font-family: var(--font); }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 760px; padding-top: 2.5rem; padding-bottom: 8rem;
}

/* ---------- empty state ---------- */
.welcome { text-align: center; margin: 9vh 0 28px; }
.welcome svg { margin-bottom: 14px; filter: drop-shadow(0 0 26px rgba(18, 194, 91, 0.45)); }
.welcome-h { font-family: var(--font); font-size: 1.9rem; font-weight: 600; letter-spacing: -0.02em; color: var(--text); }
.welcome-p { font-family: var(--font); color: var(--muted); font-size: 1rem; margin-top: 6px; }

/* ---------- messages ---------- */
.msg-user { display: flex; justify-content: flex-end; margin: 22px 0 10px; }
.msg-user .bubble {
  max-width: 78%; background: var(--bubble); border-radius: 20px;
  padding: 10px 16px; font-family: var(--font); font-size: 1rem;
  line-height: 1.55; color: var(--text); white-space: pre-wrap;
}
.msg-bot { display: flex; gap: 14px; align-items: flex-start; margin: 4px 0 18px; }
.msg-bot .avatar { flex: 0 0 28px; margin-top: 2px; }
.msg-bot .body { flex: 1; min-width: 0; }
.msg-bot .body p {
  font-family: var(--font); font-size: 1rem; line-height: 1.7;
  color: var(--text); margin: 0 0 0.75em;
}
.msg-bot .body p:last-child { margin-bottom: 0; }
.msg-bot .body.muted p { color: var(--muted); }

.cite {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 1.35em; height: 1.35em; padding: 0 0.35em; margin: 0 0.12em;
  border-radius: 999px; background: var(--chip); color: var(--text);
  font-family: var(--font); font-size: 0.72em; font-weight: 600;
  vertical-align: 0.15em;
}
.thinking { color: var(--muted); font-family: var(--font); }
.caret {
  display: inline-block; width: 2px; height: 1.05em; background: var(--text);
  vertical-align: -0.15em; margin-left: 2px; animation: blink 1s steps(2) infinite;
}
@keyframes blink { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .caret { animation: none; } }

/* ---------- source cards ---------- */
.sources { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 8px; margin-top: 14px; }
.source {
  border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px;
  background: var(--card); font-family: var(--font);
}
.source-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.source-top .cite { margin: 0; vertical-align: 0; }
.source-page { font-size: 0.8rem; color: var(--muted); }
.source-title {
  font-size: 0.86rem; font-weight: 600; color: var(--text); line-height: 1.35;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.source-id { font-size: 0.72rem; color: var(--muted); margin-top: 4px; word-break: break-all; }
.meta { font-family: var(--font); font-size: 0.8rem; color: var(--muted); margin-top: 10px; }

/* ---------- example cards (main area buttons) ---------- */
[data-testid="stMain"] .stButton button, section.main .stButton button {
  width: 100%; min-height: 4.2rem; background: var(--card);
  border: 1px solid var(--line); border-radius: 14px;
  justify-content: flex-start; text-align: left; padding: 10px 14px;
  color: var(--text); transition: background 0.15s ease, border-color 0.15s ease;
}
[data-testid="stMain"] .stButton button:hover, section.main .stButton button:hover {
  background: var(--hover); border-color: rgba(18, 194, 91, 0.45); color: var(--text);
}

/* ---------- input bar ---------- */
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: var(--bg) !important; }
[data-testid="stChatInput"] {
  background: var(--card) !important; border: 1px solid var(--line) !important;
  border-radius: 26px !important; box-shadow: 0 8px 28px rgba(0, 0, 0, 0.55);
}
[data-testid="stChatInput"]:focus-within {
  border-color: rgba(18, 194, 91, 0.55) !important;
  box-shadow: 0 0 0 3px rgba(18, 194, 91, 0.12), 0 8px 28px rgba(0, 0, 0, 0.55);
}
[data-testid="stChatInput"] textarea { color: var(--text) !important; font-family: var(--font) !important; }
[data-testid="stChatInputSubmitButton"] { background: var(--brand) !important; border-radius: 999px !important; }
[data-testid="stChatInputSubmitButton"] svg { fill: #FFFFFF !important; color: #FFFFFF !important; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: var(--side); border-right: 1px solid var(--line); }
.brand { display: flex; align-items: center; gap: 10px; margin: 2px 0 16px; }
.brand-name { font-family: var(--font); font-weight: 700; font-size: 1.15rem; color: var(--text); }
.side-label { font-family: var(--font); font-size: 0.78rem; font-weight: 600; color: var(--muted); margin: 18px 0 4px 4px; }
.side-note { font-family: var(--font); font-size: 0.78rem; color: var(--muted); line-height: 1.5; margin: 14px 4px 0; }
.book { font-family: var(--font); font-size: 0.82rem; color: var(--text); padding: 5px 0; line-height: 1.35; }
.book span { display: block; font-size: 0.74rem; color: var(--muted); }

[data-testid="stSidebar"] .stButton button {
  width: 100%; justify-content: flex-start; text-align: left;
  background: transparent; border: none; border-radius: 10px;
  padding: 6px 10px; min-height: 2.2rem; color: var(--text);
}
[data-testid="stSidebar"] .stButton button:hover { background: var(--hover); color: var(--text); }
[data-testid="stSidebar"] .stButton button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
  background: var(--active); color: var(--text); font-weight: 600;
}
[data-testid="stSidebar"] .stButton:first-of-type button {
  border: 1px solid var(--line); background: var(--card);
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
  background: var(--card); border: 1px solid var(--line) !important; border-radius: 12px;
}
.stButton button:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)
books = load_books()


# ---------- conversations ----------
if "chats" not in st.session_state:
    st.session_state.chats = [{"title": "New chat", "messages": []}]
    st.session_state.current = 0
if "pending" not in st.session_state:
    st.session_state.pending = None


def new_chat():
    chats = st.session_state.chats
    if chats[st.session_state.current]["messages"]:
        chats.append({"title": "New chat", "messages": []})
        st.session_state.current = len(chats) - 1


# ---------- html builders ----------
def answer_html(text, caret=False):
    safe = escape(text)
    safe = re.sub(r"\[(\d+)\]", r'<span class="cite">\1</span>', safe)
    paras = [p.strip() for p in safe.split("\n") if p.strip()] or [""]
    if caret:
        paras[-1] += '<span class="caret"></span>'
    return "".join(f"<p>{p}</p>" for p in paras)


def sources_html(sources):
    if not sources:
        return ""
    cards = "".join(
        f'<div class="source"><div class="source-top"><span class="cite">{s["n"]}</span>'
        f'<span class="source-page">PDF page {s["page"]}</span></div>'
        f'<div class="source-title" title="{escape(s["title"])}">{escape(s["title"])}</div>'
        f'<div class="source-id">{escape(s["chunk_id"])}</div></div>'
        for s in sources
    )
    return f'<div class="sources">{cards}</div>'


def user_html(text):
    return f'<div class="msg-user"><div class="bubble">{escape(text)}</div></div>'


def bot_html(body, extra="", muted=False):
    cls = "body muted" if muted else "body"
    return (
        f'<div class="msg-bot"><div class="avatar">{logo(28)}</div>'
        f'<div class="{cls}">{body}{extra}</div></div>'
    )


def finished_bot(m):
    if m["insufficient"]:
        body = "<p>I couldn't find this in the books on the shelf, so I won't guess.</p>"
        meta = f'<div class="meta">Checked in {m["time"]:.1f} s</div>'
        return bot_html(body, meta, muted=True)
    n = len(m["sources"])
    meta = f'<div class="meta">{m["time"]:.1f} s, {n} source{"s" if n != 1 else ""}</div>'
    return bot_html(answer_html(m["answer"]), sources_html(m["sources"]) + meta)


# ---------- sidebar ----------
with st.sidebar:
    st.markdown(
        f'<div class="brand">{logo(30)}<div class="brand-name">{BOT_NAME}</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("＋  New chat", key="new_chat"):
        new_chat()
        st.rerun()

    history = [(i, c) for i, c in enumerate(st.session_state.chats) if c["messages"]]
    if history:
        st.markdown('<div class="side-label">Recent</div>', unsafe_allow_html=True)
        for i, c in reversed(history):
            kind = "primary" if i == st.session_state.current else "secondary"
            if st.button(c["title"], key=f"chat{i}", type=kind):
                st.session_state.current = i
                st.rerun()

    st.markdown('<div class="side-label">Library</div>', unsafe_allow_html=True)
    with st.expander(f"{len(books)} books"):
        st.markdown(
            "".join(f'<div class="book">{escape(b["title"])}<span>{escape(b["author"])}</span></div>'
                    for b in books),
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="side-note">Runs offline with {MODEL}. Answers come only from the library, '
        f'so check important answers against the cited pages.</div>',
        unsafe_allow_html=True,
    )

# ---------- main ----------
chat = st.session_state.chats[st.session_state.current]

typed = st.chat_input(f"Message {BOT_NAME}")
question = typed or st.session_state.pending
st.session_state.pending = None

if not chat["messages"] and not question:
    st.markdown(
        f'<div class="welcome">{logo(52)}'
        f'<div class="welcome-h">What would you like to know?</div>'
        f'<div class="welcome-p">Answers come from {len(books)} data science textbooks, '
        f'with the page for every claim.</div></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, (label, prompt_text) in enumerate(EXAMPLES):
        if cols[i % 2].button(f"**{label}**  \n{prompt_text}", key=f"ex{i}"):
            st.session_state.pending = prompt_text
            st.rerun()

for m in chat["messages"]:
    st.markdown(user_html(m["question"]), unsafe_allow_html=True)
    st.markdown(finished_bot(m), unsafe_allow_html=True)

if question:
    if not chat["messages"]:
        chat["title"] = question if len(question) <= 38 else question[:36].rstrip() + "…"

    st.markdown(user_html(question), unsafe_allow_html=True)
    slot = st.empty()
    start = time.time()
    slot.markdown(bot_html('<p class="thinking">Searching the library…</p>'), unsafe_allow_html=True)

    results, prompt = prepare(question)
    if results is None:
        result = no_evidence()
    else:
        text = ""
        for piece in stream_tokens(prompt):
            text += piece
            slot.markdown(bot_html(answer_html(text, caret=True)), unsafe_allow_html=True)
        result = finalize(text, results)

    m = {
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "insufficient": result["insufficient_evidence"],
        "time": time.time() - start,
    }
    slot.markdown(finished_bot(m), unsafe_allow_html=True)
    chat["messages"].append(m)
    st.rerun()