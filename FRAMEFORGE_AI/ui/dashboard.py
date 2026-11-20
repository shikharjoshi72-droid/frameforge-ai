"""Dashboard, New Production and My Projects."""
from datetime import date

import streamlit as st

from core import production_planner
from ui import theme
from ui.common import open_project

GENRES = ["Drama", "Comedy", "Thriller", "Horror", "Sci-Fi", "Romance", "Action", "Documentary", "Animation", "Other"]


def render_dashboard(repo, pid):
    st.title("Dashboard")
    stats = repo.dashboard_stats()
    if stats["projects"] == 0:
        theme.empty("No productions yet", "Create your first production to turn a screenplay into a Black Book.")
        if st.button("Create a new production", type="primary"):
            st.session_state["_goto"] = "New Production"
            st.rerun()
        return
    cols = st.columns(6)
    for col, (label, key) in zip(cols, [("Projects", "projects"), ("Analysed", "analysed"), ("Scenes", "scenes"),
                                        ("Characters", "characters"), ("Locations", "locations"), ("Completion %", "completion")]):
        with col:
            theme.metric(label, stats[key])
    st.write("")
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Recent productions")
        for p in repo.list_projects()[:6]:
            c1, c2, c3 = st.columns([4, 2, 2])
            c1.markdown(f"**{p['title']}**  \n<span style='color:#8C97BD;font-size:.8rem'>{p['id']} - {p.get('genre') or 'no genre'}</span>",
                        unsafe_allow_html=True)
            stages = repo.get_stages(p["id"])
            done = stages.get("story_analysis", {}).get("status") == "DONE"
            c2.markdown(theme.pill("Analysed" if repo.list_scenes(p["id"]) else "Not analysed",
                                   "ok" if done else "warn"), unsafe_allow_html=True)
            if c3.button("Open", key=f"open_{p['id']}"):
                open_project(p["id"], "Script Analysis")
    with right:
        st.subheader("Upcoming shooting days")
        up = repo.upcoming_days()
        if up:
            for d in up:
                st.markdown(f"**{d['shoot_date']}** - {d['title']} - Day {d['day_number']} ({d['location_names']})")
        else:
            st.caption("No dated shooting days. Set a production start date and generate a schedule.")
        st.subheader("Pending tasks")
        if pid:
            for item in production_planner.pending_information(repo, pid)[:6]:
                st.markdown(f"- {item}")
        else:
            st.caption("Select a project to see its pending tasks.")


def render_new_production(repo, pid):
    st.title("New Production")
    with st.form("new_prod"):
        title = st.text_input("Movie title *")
        c1, c2 = st.columns(2)
        company = c1.text_input("Production company")
        director = c2.text_input("Director")
        genre = c1.selectbox("Genre", GENRES)
        runtime = c2.number_input("Target runtime (minutes)", min_value=0, max_value=600, value=0, step=5)
        use_date = st.checkbox("Set a production start date")
        start = st.date_input("Production start date", value=date.today())
        desc = st.text_area("Project description")
        ok = st.form_submit_button("Create production", type="primary")
    if ok:
        if not title.strip():
            st.error("A movie title is required.")
            return
        new_id = repo.create_project(title, company, director, genre, runtime or None,
                                     start.isoformat() if use_date else None, desc)
        st.success(f"Created {title} ({new_id}). Opening screenplay upload...")
        open_project(new_id, "Script Analysis")


def render_projects(repo, pid):
    st.title("My Projects")
    projects = repo.list_projects()
    if not projects:
        theme.empty("No productions yet", "Use New Production to create one.")
        return
    for p in projects:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([5, 2, 1, 1])
            c1.markdown(f"**{p['title']}**  \n<span style='color:#8C97BD;font-size:.8rem'>{p['id']} - created {p['created_at'][:10]} - "
                        f"status {p['review_status']}</span>", unsafe_allow_html=True)
            c2.caption(f"{len(repo.list_scenes(p['id']))} scenes")
            if c3.button("Open", key=f"po_{p['id']}"):
                open_project(p["id"], "Script Analysis")
            with c4.popover("Delete"):
                st.warning(f"Permanently delete {p['title']} and all its data?")
                if st.button("Yes, delete", key=f"pd_{p['id']}", type="primary"):
                    repo.delete_project(p["id"])
                    if st.session_state.get("project_id") == p["id"]:
                        st.session_state["_set_project"] = None
                    st.rerun()
