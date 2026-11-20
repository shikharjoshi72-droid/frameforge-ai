"""Shooting schedule: generate (deterministic), review, edit, approve."""
import pandas as pd
import streamlit as st

from config.constants import TIMES_OF_DAY  # noqa: F401
from core import schedule_generator as sg
from ui import theme
from ui.common import STRETCH, flash, get_client, has_api_key, require_project, require_scenes, safe


def render(repo, pid):
    st.title("Shooting Schedule")
    project = require_project(repo, pid)
    scenes = require_scenes(repo, pid)
    approved = bool(project["schedule_approved"])
    st.markdown(theme.pill("APPROVED" if approved else "PROPOSED - not approved", "ok" if approved else "warn"), unsafe_allow_html=True)
    st.caption("Story order and shooting order differ. The proposal groups scenes by location, then time of day, using fixed, "
               "explainable rules. Nothing here is a confirmed booking, date or availability.")
    with st.expander("Scheduling parameters", expanded=not repo.list_shooting_days(pid)):
        c1, c2, c3 = st.columns(3)
        capacity = c1.number_input("Shooting minutes per day", 120, 1200, 600, 30)
        max_loc = c2.number_input("Max locations per day", 1, 4, 2)
        move = c3.number_input("Company move (minutes)", 0, 240, 60, 15)
        skip = st.checkbox("Skip weekends when assigning dates", value=True)
        start = project.get("start_date")
        st.caption(f"Production start date: {start or 'not set - dates will be Pending'} (edit in Black Book > Project details).")
        avail = st.text_area("Known actor unavailability (optional), one per line", placeholder="ANNA: 2026-12-03, day 4")
        if st.button("Generate proposed schedule", type="primary"):
            res = sg.generate_schedule(scenes, start, capacity, max_loc, move, skip, sg.parse_availability(avail))
            repo.save_schedule(pid, res["days"])
            st.session_state[f"conf_{pid}"] = res["conflicts"]
            flash("success", f"Proposed {res['stats']['days']} shooting day(s), {res['stats']['company_moves']} company move(s). Review before approving.")
            st.rerun()
    days = repo.list_shooting_days(pid)
    if not days:
        theme.empty("No schedule yet", "Generate a proposed schedule from your scenes.")
        return
    conflicts = st.session_state.get(f"conf_{pid}", [])
    if conflicts:
        st.warning("Conflicts to resolve:\n" + "\n".join(f"- {c['message']}" for c in conflicts))
    scheduled = {s["id"] for d in days for s in d["scenes"]}
    orphan = [s for s in scenes if s["id"] not in scheduled]
    if orphan:
        st.error(f"{len(orphan)} scene(s) are unscheduled: " + ", ".join(str(s["scene_number"]) for s in orphan))
    for d in days:
        with st.expander(f"Day {d['day_number']} - {d['shoot_date'] or 'date pending'} - {d['call_type']} - {d['location_names']} "
                         f"({len(d['scenes'])} scenes, ~{d['est_minutes']} min)"):
            st.caption(d["explanation"])
            st.dataframe(pd.DataFrame([{"Scene": s["scene_number"], "Heading": s["heading"], "Cast": ", ".join(s["characters"]),
                                        "Complexity": s["complexity"], "Est. min": sg.estimate_minutes(s)} for s in d["scenes"]]),
                         hide_index=True, **STRETCH)
    st.subheader("Edit schedule")
    day_opts = [d["day_number"] for d in days]
    by_num = {d["day_number"]: d for d in days}
    cur = {s["id"]: d["day_number"] for d in days for s in d["scenes"]}
    df = pd.DataFrame([{"id": s["id"], "scene": s["scene_number"], "heading": s["heading"], "location": s["location"],
                        "day": cur.get(s["id"])} for s in scenes])
    edited = st.data_editor(df, column_config={"id": None, "scene": st.column_config.TextColumn("Scene", disabled=True),
                                               "heading": st.column_config.TextColumn("Heading", disabled=True),
                                               "location": st.column_config.TextColumn("Location", disabled=True),
                                               "day": st.column_config.SelectboxColumn("Shooting day", options=day_opts)},
                            hide_index=True, key=f"sched_{pid}", **STRETCH)
    ddf = pd.DataFrame([{"id": d["id"], "day": d["day_number"], "shoot_date": d["shoot_date"] or "", "call_type": d["call_type"]}
                        for d in days])
    dedit = st.data_editor(ddf, column_config={"id": None, "day": st.column_config.NumberColumn("Day", disabled=True),
                                               "shoot_date": st.column_config.TextColumn("Date (YYYY-MM-DD)"),
                                               "call_type": st.column_config.SelectboxColumn("Unit", options=["DAY", "NIGHT"])},
                           hide_index=True, key=f"days_{pid}", **STRETCH)
    c1, c2, c3 = st.columns(3)
    if c1.button("Save schedule edits"):
        try:
            for r in edited.to_dict("records"):
                if r["day"] == r["day"] and r["day"] is not None:
                    if cur.get(r["id"]) != int(r["day"]):
                        repo.move_scene_to_day(r["id"], by_num[int(r["day"])]["id"])
                else:
                    repo.move_scene_to_day(r["id"], None)
            for r in dedit.to_dict("records"):
                dt = (r["shoot_date"] or "").strip()
                if dt:
                    from datetime import date
                    date.fromisoformat(dt)
                repo.update_day(r["id"], shoot_date=dt or None, call_type=r["call_type"])
            repo.set_schedule_approved(pid, False)
        except ValueError:
            st.error("Dates must use YYYY-MM-DD.")
        else:
            flash("success", "Schedule saved. Approval was reset - review and approve again.")
            st.rerun()
    if approved:
        if c2.button("Withdraw approval"):
            repo.set_schedule_approved(pid, False)
            st.rerun()
    elif c2.button("Approve schedule", type="primary", disabled=bool(orphan)):
        repo.set_schedule_approved(pid, True)
        flash("success", "Schedule approved and saved.")
        st.rerun()
    st.subheader("AI scheduling suggestions")
    st.caption("Advisory only. Suggestions never change the schedule automatically.")
    if st.button("Ask AI for improvements", disabled=not has_api_key()):
        with st.spinner("Thinking..."):
            txt = safe(sg.ai_suggestions, get_client(), days, scenes, conflicts)
            if txt:
                st.session_state[f"aisug_{pid}"] = txt
    if st.session_state.get(f"aisug_{pid}"):
        st.markdown(st.session_state[f"aisug_{pid}"])
