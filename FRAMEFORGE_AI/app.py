"""FRAMEFORGE AI - From Script to Production. One Intelligent Black Book.   Run: streamlit run app.py"""
import streamlit as st

from config.constants import APP_NAME, NAV_PAGES, SUBTITLE
from database.repository import Repository
from ui import (analysis, assistant, blackbook_preview, call_sheets, dashboard, progress, registers, scene_breakdown,
                schedule, settings, theme)
from ui.common import show_flash

st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide")


@st.cache_resource
def get_repo() -> Repository:
    return Repository()


repo = get_repo()
theme.inject()

# programmatic navigation / project switching must happen before the widgets are created
if "_goto" in st.session_state:
    st.session_state["nav"] = st.session_state.pop("_goto")
if "_set_project" in st.session_state:
    st.session_state["project_id"] = st.session_state.pop("_set_project")

with st.sidebar:
    st.markdown(f'<div class="ff-brand">FRAME<span>FORGE</span> AI</div><div class="ff-sub">{SUBTITLE}</div>', unsafe_allow_html=True)
    projects = repo.list_projects()
    ids = [p["id"] for p in projects]
    titles = {p["id"]: f"{p['title']} ({p['id']})" for p in projects}
    if st.session_state.get("project_id") not in ids:
        st.session_state["project_id"] = ids[0] if ids else None
    pid = st.selectbox("Production", ids, format_func=lambda i: titles[i], key="project_id", placeholder="No productions yet") if ids else None
    if pid:
        repo.touch_project(pid)
    page = st.radio("Navigate", NAV_PAGES, key="nav", label_visibility="collapsed")

show_flash()
ROUTES = {
    "Dashboard": dashboard.render_dashboard, "New Production": dashboard.render_new_production,
    "My Projects": dashboard.render_projects, "Script Analysis": analysis.render,
    "Scene Breakdown": scene_breakdown.render, "Character Register": registers.render_characters,
    "Locations": registers.render_locations, "Production Resources": registers.render_resources,
    "Shooting Schedule": schedule.render, "Call Sheets": call_sheets.render, "Production Progress": progress.render,
    "Black Book": blackbook_preview.render, "AI Production Assistant": assistant.render, "Settings": settings.render,
}
try:
    ROUTES[page](repo, pid)
except Exception as exc:  # noqa: BLE001 - never show a raw traceback to the user
    st.error(f"Something went wrong on this page: {exc.__class__.__name__}: {exc}")
