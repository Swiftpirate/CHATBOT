import json
import time
from pathlib import Path

import streamlit as st
from generate import prepare, stream_tokens, finalize, no_evidence, MODEL

# ---------- settings you can change ----------
BOT_NAME = "DataSage"
USER_AVATAR = "🧑‍🎓"
BOT_AVATAR = "📗"
EXAMPLES = [
    "What is overfitting?",
    "What is PageRank?",
    "What is gradient descent?",
    "What is TF-IDF?",
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


def logo(size, gid):
    """Vibrant green logo: an open book with a spark (pure SVG, no image file)."""
    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#5CFF9D"/>
      <stop offset="0.55" stop-color="#00E676"/>
      <stop offset="1" stop-color="#00B248"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="18" fill="url(#{gid})"/>
  <path d="M12 22c6.5-3.2 13-3.2 19.5 1v24c-6.5-4.2-13-4.2-19.5-1z" fill="#06210F"/>
  <path d="M52 22c-6.5-3.2-13-3.2-19.5 1v24c6.5-4.2 13-4.2 19.5-1z" fill="#06210F" opacity="0.82"/>
  <path d="M17 29h9M17 34h9M38 29h9M38 34h9" stroke="#5CFF9D" stroke-width="2" stroke-linecap="round" opacity="0.9"/>
  <circle cx="50" cy="12" r="3.2" fill="#FFFFFF"/>
  <path d="M50 5.5v2.5M50 16v2.5M43.5 12h2.5M54 12h2.5" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"/>
</svg>"""


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');

:root {
  --green: #00E676;
  --green-bright: #5CFF9D;
  --bg: #070C09;
  --card: #0F1813;
  --card-2: #13201A;
  --border: #1D2E25;
  --text: #E8F5EC;
  --muted: #8BA596;
}

html, body, .stApp, [data-testid="stMarkdownContainer"] { font-family: 'Inter', sans-serif; }

.stApp {
  background:
    radial-gradient(900px 500px at 50% -15%, rgba(0, 230, 118, 0.16), transparent 60%),
    radial-gradient(600px 400px at 100% 100%, rgba(0, 230, 118, 0.06), transparent 60%),
    var(--bg);
}

#MainMenu, footer { visibility: hidden; }

/* ---------- hero ---------- */
.hero { display: flex; align-items: center; gap: 18px; margin: 6px 0 6px; }
.hero svg { filter: drop-shadow(0 0 22px rgba(0, 230, 118, 0.45)); flex-shrink: 0; }
.hero h1 {
  font-family: 'Space Grotesk', sans-serif; font-weight: 700;
  font-size: 2.6rem; line-height: 1; margin: 0; padding: 0;
  background: linear-gradient(90deg, #5CFF9D, #00E676 45%, #B9F6CA);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p { color: var(--muted); margin: 6px 0 0; font-size: 0.95rem; }

.pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 22px; }
.pill {
  font-size: 0.78rem; color: var(--green-bright);
  background: rgba(0, 230, 118, 0.08); border: 1px solid rgba(0, 230, 118, 0.28);
  padding: 4px 11px; border-radius: 999px;
}

/* ---------- chat messages ---------- */
[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 18px; padding: 14px 16px; margin-bottom: 12px;
}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]),
[data-testid="stChatMessage"]:nth-of-type(odd) { background: var(--card-2); }

/* ---------- chat input ---------- */
[data-testid="stChatInput"] {
  border: 1px solid rgba(0, 230, 118, 0.35) !important; border-radius: 16px !important;
  box-shadow: 0 0 24px rgba(0, 230, 118, 0.10);
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--green) !important; box-shadow: 0 0 28px rgba(0, 230, 118, 0.25);
}

/* ---------- buttons ---------- */
.stButton button {
  border-radius: 999px; border: 1px solid var(--border);
  background: var(--card); color: var(--text); transition: all 0.15s ease;
}
.stButton button:hover {
  border-color: var(--green); color: var(--green-bright);
  box-shadow: 0 0 16px rgba(0, 230, 118, 0.22);
}

/* ---------- sources ---------- */
[data-testid="stExpander"] {
  border: 1px solid var(--border) !important; border-radius: 12px !important; background: var(--bg);
}
.source { display: flex; gap: 12px; padding: 8px 2px; border-bottom: 1px dashed var(--border); }
.source:last-child { border-bottom: none; }
.num {
  flex-shrink: 0; width: 26px; height: 26px; border-radius: 8px;
  background: var(--green); color: #04150A; font-weight: 700; font-size: 0.85rem;
  display: flex; align-items: center; justify-content: center;
}
.src-title { font-weight: 600; color: var(--text); }
.meta { color: var(--muted); font-size: 0.8rem; }
.chunk { font-family: monospace; font-size: 0.75rem; color: var(--green-bright); opacity: 0.85; }

.warn {
  margin-top: 8px; padding: 8px 12px; border-radius: 10px; font-size: 0.85rem;
  color: #FFD180; background: rgba(255, 171, 0, 0.08); border: 1px solid rgba(255, 171, 0, 0.3);
}
.stats { margin-top: 8px; color: var(--muted); font-size: 0.78rem; }
.stats b { color: var(--green-bright); font-weight: 600; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: #0A120E; border-right: 1px solid var(--border); }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.brand svg { filter: drop-shadow(0 0 12px rgba(0, 230, 118, 0.4)); }
.brand-name { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.3rem; color: var(--green-bright); }
.step { display: flex; gap: 10px; margin: 8px 0; font-size: 0.88rem; color: var(--text); }
.step .num { width: 22px; height: 22px; font-size: 0.75rem; border-radius: 6px; }
.book { padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
.book:last-child { border-bottom: none; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)
books = load_books()

# ---------- sidebar ----------
with st.sidebar:
    st.markdown(
        f'<div class="brand">{logo(46, "g_side")}<div>'
        f'<div class="brand-name">{BOT_NAME}</div>'
        f'<div class="meta">Book-grounded AI assistant</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("#### How it works")
    st.markdown(
        '<div class="step"><span class="num">1</span>Searches your question across the books</div>'
        '<div class="step"><span class="num">2</span>Picks the most relevant passages</div>'
        '<div class="step"><span class="num">3</span>Writes an answer citing each passage</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="pills"><span class="pill">{len(books)} books</span>'
        f'<span class="pill">{MODEL}</span><span class="pill">Runs offline</span></div>',
        unsafe_allow_html=True,
    )
    with st.expander(f"📚 Library ({len(books)} books)"):
        st.markdown(
            "".join(
                f'<div class="book"><b>{b["title"]}</b><br>'
                f'<span class="meta">{b["author"]}</span></div>'
                for b in books
            ),
            unsafe_allow_html=True,
        )
    st.write("")
    if st.button("🗑️  Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ---------- hero ----------
st.markdown(
    f'<div class="hero">{logo(68, "g_hero")}<div>'
    f'<h1>{BOT_NAME}</h1>'
    f'<p>Answers grounded in {len(books)} data science textbooks, with every claim cited.</p>'
    f'</div></div>',
    unsafe_allow_html=True,
)


# ---------- helpers ----------
def render_assistant(msg):
    st.markdown(msg["content"])
    if msg.get("insufficient"):
        st.markdown('<div class="warn">⚠️ No supporting passage found in the books.</div>',
                    unsafe_allow_html=True)
    if msg.get("sources"):
        with st.expander(f"📚 Sources ({len(msg['sources'])})"):
            st.markdown(
                "".join(
                    f'<div class="source"><span class="num">{s["n"]}</span><div>'
                    f'<div class="src-title">{s["title"]}</div>'
                    f'<div class="meta">{s["author"]} · {s["edition"]} · PDF page {s["page"]}</div>'
                    f'<div class="chunk">{s["chunk_id"]}</div></div></div>'
                    for s in msg["sources"]
                ),
                unsafe_allow_html=True,
            )
    if msg.get("time") is not None:
        n = len(msg.get("sources", []))
        st.markdown(
            f'<div class="stats">⚡ <b>{msg["time"]:.1f}s</b> · {n} source{"s" if n != 1 else ""}</div>',
            unsafe_allow_html=True,
        )


# ---------- state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None

typed = st.chat_input("Ask anything about the books...")
question = typed or st.session_state.pending
st.session_state.pending = None

# ---------- history ----------
for msg in st.session_state.messages:
    avatar = USER_AVATAR if msg["role"] == "user" else BOT_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_assistant(msg)

# ---------- example questions (only on an empty chat) ----------
if not st.session_state.messages and not question:
    st.markdown('<div class="meta" style="margin-bottom:8px;">Try one of these:</div>',
                unsafe_allow_html=True)
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        if cols[i % 2].button(ex, key=f"ex{i}"):
            st.session_state.pending = ex
            st.rerun()

# ---------- answer a new question ----------
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(question)

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        placeholder = st.empty()
        start = time.time()

        with st.spinner("Searching the books..."):
            results, prompt = prepare(question)

        if results is None:
            result = no_evidence()
        else:
            text = ""
            for piece in stream_tokens(prompt):
                text += piece
                placeholder.markdown(text + " ▌")
            result = finalize(text, results)

        placeholder.empty()
        msg = {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "insufficient": result["insufficient_evidence"],
            "time": time.time() - start,
        }
        render_assistant(msg)

    st.session_state.messages.append(msg)
