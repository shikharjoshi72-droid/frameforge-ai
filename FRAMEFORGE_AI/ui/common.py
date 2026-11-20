"""Shared UI helpers."""
import streamlit as st

import re

from ai.nvidia_client import NvidiaClient
from config.settings import get_settings


def _ver():
    nums = re.findall(r"\d+", st.__version__)[:2]
    return tuple(int(n) for n in nums) if len(nums) == 2 else (1, 40)


# Streamlit >= 1.50 uses width="stretch"; older versions use use_container_width=True.
STRETCH = {"width": "stretch"} if _ver() >= (1, 50) else {"use_container_width": True}


def get_client() -> NvidiaClient:
    s = get_settings()
    key = s.nvidia_api_key or st.session_state.get("session_api_key", "")
    model = st.session_state.get("session_model") or s.nvidia_model
    return NvidiaClient(key, model, s.nvidia_base_url, s.request_timeout, s.max_retries, s.disable_thinking, s.max_tokens)


def has_api_key() -> bool:
    return bool(get_settings().nvidia_api_key or st.session_state.get("session_api_key"))


def goto(page: str):
    st.session_state["_goto"] = page
    st.rerun()


def open_project(pid: str, page: str | None = None):
    st.session_state["_set_project"] = pid
    if page:
        st.session_state["_goto"] = page
    st.rerun()


def require_project(repo, pid):
    if not pid:
        st.info("Select or create a production in the sidebar to continue.")
        st.stop()
    p = repo.get_project(pid)
    if not p:
        st.error("Project not found.")
        st.stop()
    return p


def require_scenes(repo, pid):
    scenes = repo.list_scenes(pid)
    if not scenes:
        st.info("No scenes yet. Upload and analyse a screenplay in **Script Analysis** first.")
        st.stop()
    return scenes


def flash(kind: str, msg: str):
    st.session_state.setdefault("_flash", []).append((kind, msg))


def show_flash():
    for kind, msg in st.session_state.pop("_flash", []):
        getattr(st, kind)(msg)


def safe(fn, *args, **kwargs):
    """Run an action, surfacing friendly errors instead of crashing the page."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - last line of defence for the UI
        st.error(f"{exc.__class__.__name__}: {exc}")
        return None
