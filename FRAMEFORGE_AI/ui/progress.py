"""Production progress tracking with Plotly charts (all numbers from the database)."""
import pandas as pd
import streamlit as st

from config.constants import SCENE_STATUSES
from core import production_planner
from ui import theme
from ui.common import STRETCH, flash, require_project, require_scenes

COLORS = {"Not Started": "#5C6788", "Planned": "#4C6FFF", "In Progress": "#FFD27C", "Completed": "#7CE3A1", "On Hold": "#FF8A8A"}


def render(repo, pid):
    st.title("Production Progress")
    require_project(repo, pid)
    scenes = require_scenes(repo, pid)
    m = production_planner.progress_metrics(repo, pid)
    cols = st.columns(6)
    for col, (lab, val) in zip(cols, [("Scenes", m["total"]), ("Completed", m["completed"]), ("Pending", m["pending"]),
                                       ("Completion", f"{m['pct']}%"), ("Days planned/done", f"{m['days_planned']}/{m['days_completed']}"),
                                       ("Locations covered", m["locations_covered"])]):
        with col:
            theme.metric(lab, val)
    st.caption(f"Outstanding scene requirements (non-recommended items in unfinished scenes): {m['open_requirements']}")
    try:
        import plotly.express as px
        c1, c2 = st.columns(2)
        counts = pd.DataFrame([{"status": s, "scenes": m["counts"].get(s, 0)} for s in SCENE_STATUSES])
        fig = px.pie(counts[counts.scenes > 0], names="status", values="scenes", hole=0.55, color="status", color_discrete_map=COLORS)
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", title="Scene status")
        c1.plotly_chart(fig, **STRETCH)
        loc = pd.DataFrame([{"location": s["location"] or "Unknown", "status": s["status"]} for s in scenes])
        fig2 = px.histogram(loc, x="location", color="status", color_discrete_map=COLORS, barmode="stack")
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", title="Scenes by location and status", yaxis_title="Scenes")
        c2.plotly_chart(fig2, **STRETCH)
    except ImportError:
        st.warning("Install plotly to see charts: pip install plotly")
    st.subheader("Update scene status")
    df = pd.DataFrame([{"id": s["id"], "scene": s["scene_number"], "heading": s["heading"], "status": s["status"]} for s in scenes])
    edited = st.data_editor(df, column_config={"id": None, "scene": st.column_config.TextColumn("Scene", disabled=True),
                                               "heading": st.column_config.TextColumn("Heading", disabled=True),
                                               "status": st.column_config.SelectboxColumn("Status", options=SCENE_STATUSES)},
                            hide_index=True, key=f"prog_{pid}", **STRETCH)
    if st.button("Save progress", type="primary"):
        old = {s["id"]: s["status"] for s in scenes}
        for r in edited.to_dict("records"):
            if r["status"] != old.get(r["id"]):
                repo.set_scene_status(r["id"], r["status"])
        flash("success", "Progress saved.")
        st.rerun()
    days = repo.list_shooting_days(pid)
    if days:
        st.subheader("Shooting days")
        for d in days:
            done = st.checkbox(f"Day {d['day_number']} wrapped - {d['location_names']}", value=bool(d["completed"]), key=f"dd_{d['id']}")
            if done != bool(d["completed"]):
                repo.update_day(d["id"], completed=int(done))
                st.rerun()
