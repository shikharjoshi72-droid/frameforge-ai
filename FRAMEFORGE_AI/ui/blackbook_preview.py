"""Black Book readiness, project details, review status and PDF generation/download."""
from datetime import date
from pathlib import Path

import streamlit as st

from config.constants import REVIEW_STATUSES
from core import blackbook_generator, production_planner
from ui.common import flash, require_project


def render(repo, pid):
    st.title("Black Book")
    p = require_project(repo, pid)
    scenes = repo.list_scenes(pid)
    with st.expander("Project details, review status and production notes"):
        with st.form("proj_edit"):
            c1, c2 = st.columns(2)
            title = c1.text_input("Title", p["title"])
            company = c2.text_input("Production company", p.get("company") or "")
            director = c1.text_input("Director", p.get("director") or "")
            genre = c2.text_input("Genre", p.get("genre") or "")
            runtime = c1.number_input("Target runtime (min)", 0, 600, int(p.get("target_runtime") or 0))
            sd = c2.text_input("Production start date (YYYY-MM-DD, optional)", p.get("start_date") or "")
            desc = st.text_area("Description", p.get("description") or "")
            status = st.selectbox("Review status", REVIEW_STATUSES, index=REVIEW_STATUSES.index(p["review_status"])
                                  if p["review_status"] in REVIEW_STATUSES else 0)
            notes = st.text_area("Production notes (appear in the Black Book)", p.get("notes") or "", height=120)
            if st.form_submit_button("Save details", type="primary"):
                try:
                    if sd.strip():
                        date.fromisoformat(sd.strip())
                except ValueError:
                    st.error("Start date must be YYYY-MM-DD.")
                else:
                    repo.update_project(pid, title=title, company=company, director=director, genre=genre,
                                        target_runtime=runtime or None, start_date=sd.strip() or None, description=desc,
                                        review_status=status, notes=notes)
                    flash("success", "Project details saved.")
                    st.rerun()
    st.subheader("Readiness")
    pending = production_planner.pending_information(repo, pid)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scenes", len(scenes))
    c2.metric("Characters", len(repo.list_characters(pid)))
    c3.metric("Locations", len(repo.list_locations(pid)))
    c4.metric("Shooting days", len(repo.list_shooting_days(pid)))
    if pending:
        with st.expander(f"{len(pending)} item(s) will appear under 'Pending Information'", expanded=True):
            for item in pending:
                st.markdown(f"- {item}")
    st.caption("The PDF is generated only from the saved, reviewed data above - never from raw AI output. "
               "It includes an AI-generated-information disclaimer, review status and version.")
    if st.button("Generate Black Book PDF", type="primary", disabled=not scenes):
        with st.spinner("Building and verifying the PDF..."):
            try:
                res = blackbook_generator.generate(repo, pid)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
            else:
                st.session_state[f"bb_{pid}"] = res
                st.success(f"Black Book v{res['version']} generated: {res['verification']['pages']} pages, all sections verified.")
    res = st.session_state.get(f"bb_{pid}")
    if res:
        st.download_button("Download Black Book (PDF)", res["bytes"], Path(res["path"]).name, "application/pdf", type="primary")
    prev = [d for d in repo.list_documents_by_kind(pid, "blackbook")]
    if prev:
        st.subheader("Previous versions")
        for d in prev:
            path = Path(d["stored_path"])
            if path.exists():
                st.download_button(f"{d['filename']} ({d['page_count']} pages, {d['created_at'][:16]})", path.read_bytes(),
                                   d["filename"], "application/pdf", key=f"dl_{d['id']}")
