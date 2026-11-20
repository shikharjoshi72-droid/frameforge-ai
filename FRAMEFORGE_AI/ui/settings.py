"""Settings: API status and connectivity test. The key is never displayed."""
import streamlit as st

from config.settings import get_settings
from ui.common import get_client, has_api_key


def render(repo, pid):
    st.title("Settings")
    s = get_settings()
    st.subheader("NVIDIA NIM connection")
    st.markdown(f"- API key: **{'configured' if has_api_key() else 'missing'}**  \n- Base URL: `{s.nvidia_base_url}`  \n"
                f"- Default model: `{s.nvidia_model}`  \n- Timeout: {s.request_timeout}s - Retries: {s.max_retries}")
    st.caption("Set NVIDIA_API_KEY in the .env file (never commit it). For a quick trial you can enter a key for this browser "
               "session only; it is kept in memory and never written to disk or logs.")
    key = st.text_input("Session API key (optional)", type="password")
    if key:
        st.session_state["session_api_key"] = key.strip()
    model = st.text_input("Model override for this session", st.session_state.get("session_model", ""),
                          placeholder=s.nvidia_model, help="e.g. try another Nemotron model after verifying availability")
    st.session_state["session_model"] = model.strip()
    if st.button("Test connection", type="primary"):
        with st.spinner("Contacting NVIDIA..."):
            r = get_client().test_connection()
        if r["ok"]:
            st.success(f"{r['message']} ({r['latency_s']}s)")
            if r["model_listed"] is False:
                st.warning("The model answered but was not in the models list; confirm the ID is correct.")
        else:
            st.error(r["message"])
    st.subheader("Limits")
    st.markdown(f"- Max upload: {s.max_upload_mb} MB  \n- Chunk size: ~{s.chunk_max_chars} characters, max {s.chunk_max_blocks} scenes per chunk")
    st.subheader("Data handling")
    st.markdown("Screenplay text is sent to NVIDIA's hosted API for analysis. Projects, uploads and generated PDFs are stored "
                "locally in `data/` and `generated/`.")
