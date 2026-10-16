import streamlit as st
from generate import prepare, stream_tokens, finalize, no_evidence

st.set_page_config(page_title="Data Science Book Chatbot")
st.title("Data Science Book Chatbot")
st.caption("Answers come only from the project's books, with citations.")


def format_reply(result):
    reply = result["answer"]
    if result["sources"]:
        reply += "\n\n**Sources:**\n\n" + "\n\n".join(
            f"[{s['n']}] *{s['title']}*, {s['author']} ({s['edition']}), "
            f"PDF page {s['page']} — `{s['chunk_id']}`"
            for s in result["sources"]
        )
    elif result["insufficient_evidence"]:
        reply += "\n\n_No supporting passage found in the books._"
    return reply


if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Ask a question about the books")

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()

        with st.spinner("Searching the books..."):
            results, prompt = prepare(question)

        if results is None:
            result = no_evidence()
        else:
            text = ""
            for piece in stream_tokens(prompt):
                text += piece
                placeholder.markdown(text + "▌")  # show the answer as it is written
            result = finalize(text, results)

        reply = format_reply(result)
        placeholder.markdown(reply)

    st.session_state.history.append({"role": "assistant", "content": reply})