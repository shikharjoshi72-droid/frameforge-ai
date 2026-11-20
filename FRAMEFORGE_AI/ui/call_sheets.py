"""Daily call sheets built from the schedule; missing facts stay PENDING."""
import streamlit as st

from core.schedule_generator import build_call_sheet
from exports.pdf_generator import build_call_sheet_pdf
from ui import theme
from ui.common import flash, require_project


def render(repo, pid):
    st.title("Call Sheets")
    project = require_project(repo, pid)
    days = repo.list_shooting_days(pid)
    if not days:
        theme.empty("No shooting days", "Generate a schedule first (Shooting Schedule).")
        return
    if not project["schedule_approved"]:
        st.warning("The schedule is still a PROPOSAL. Call sheets will be marked PROPOSED until you approve it.")
    day = st.selectbox("Shooting day", days, format_func=lambda d: f"Day {d['day_number']} - {d['shoot_date'] or 'date pending'} - {d['location_names']}")
    saved = repo.get_call_sheet(day["id"])
    st.caption("Only enter what is confirmed. Blank fields appear as PENDING; nothing is invented.")
    with st.form(f"cs_{day['id']}"):
        c1, c2 = st.columns(2)
        call = c1.text_input("Reporting (call) time", saved.get("call_time", ""), placeholder="e.g. 06:30")
        wrap = c2.text_input("Expected wrap", saved.get("wrap_time", ""), placeholder="e.g. 17:00")
        crew = st.text_area("Required crew", saved.get("crew", ""), placeholder="Roles/names as confirmed by production")
        emergency = st.text_input("Emergency contact", saved.get("emergency_contact", ""))
        instr = st.text_area("Special instructions", saved.get("instructions", ""))
        if st.form_submit_button("Save call sheet details", type="primary"):
            repo.save_call_sheet(pid, day["id"], call_time=call, wrap_time=wrap, crew=crew, emergency_contact=emergency,
                                 instructions=instr)
            flash("success", "Call sheet details saved.")
            st.rerun()
    cs = build_call_sheet(project, day, repo.get_call_sheet(day["id"]))
    st.subheader(f"Day {cs['day_number']} - {cs['date']}  [{cs['status']}]")
    a, b = st.columns(2)
    a.markdown(f"**Production:** {cs['production']}  \n**Location:** {cs['location']}  \n**Unit:** {cs['call_type']}  \n"
               f"**Call:** {cs['call_time']} - **Wrap:** {cs['wrap_time']}")
    b.markdown(f"**Cast:** {', '.join(cs['cast']) or 'PENDING'}  \n**Crew:** {cs['crew']}  \n**Emergency:** {cs['emergency_contact']}")
    st.table([{"Scene": s["number"], "Heading": s["heading"], "Pages": s["pages"], "Cast": s["cast"]} for s in cs["scenes"]])
    st.markdown(f"**Props:** {', '.join(cs['props']) or 'none listed'}  \n**Equipment:** {', '.join(cs['equipment']) or 'none listed'}  \n"
                f"**Costumes:** {', '.join(cs['costumes']) or 'none listed'}  \n**Special:** {'; '.join(cs['special']) or 'none'}")
    st.download_button("Download call sheet PDF", build_call_sheet_pdf(cs), f"CallSheet_{pid}_Day{cs['day_number']}.pdf",
                       "application/pdf", type="primary")
