"""AI Production Assistant grounded in the selected project's saved data."""
import streamlit as st

from ai import ai_assistant
from ai.nvidia_client import NvidiaError
from ui.common import get_client, has_api_key, require_project, require_scenes

QUICK = ["How many scenes are in this screenplay?", "Give me the complete list of locations.", "Which scenes are pending?",
         "What equipment is required for night scenes?", "Suggest a better shooting order.",
         "What information is missing from my Black Book?"]


def render(repo, pid):
    st.title("AI Production Assistant")
    p = require_project(repo, pid)
    require_scenes(repo, pid)
    st.caption(f"Answers come only from the saved data of '{p['title']}'. If something is not in the data, the assistant says so.")
    if not has_api_key():
        st.error("No NVIDIA API key configured (see Settings).")
        return
    key = f"chat_{pid}"
    hist = st.session_state.setdefault(key, [])
    cols = st.columns(3)
    asked = None
    for i, q in enumerate(QUICK):
        if cols[i % 3].button(q, key=f"q{i}"):
            asked = q
    for m in hist:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    asked = st.chat_input("Ask about your production...") or asked
    if asked:
        with st.chat_message("user"):
            st.markdown(asked)
        with st.chat_message("assistant"):
            with st.spinner("Checking project data..."):
                try:
                    ans = ai_assistant.ask(get_client(), repo, pid, asked, hist)
                except NvidiaError as exc:
                    ans = f"I could not reach the model: {exc}"
                except Exception as exc:  # noqa: BLE001
                    ans = f"Something went wrong: {exc}"
            st.markdown(ans)
        hist += [{"role": "user", "content": asked}, {"role": "assistant", "content": ans}]
