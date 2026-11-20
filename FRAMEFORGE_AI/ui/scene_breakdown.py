"""Editable scene breakdown with per-scene re-analysis."""
import pandas as pd
import streamlit as st

from config.constants import COMPLEXITY, INT_EXT, TIMES_OF_DAY
from core import production_planner, scene_extractor
from core.utils import item_names, join_csv, names_to_items, split_csv
from ui.common import STRETCH, flash, get_client, has_api_key, require_project, require_scenes, safe

RES = [("props", "props"), ("costumes", "costumes"), ("vehicles", "vehicles"), ("special_effects", "special_effects"),
       ("equipment", "equipment")]


def render(repo, pid):
    st.title("Scene Breakdown")
    require_project(repo, pid)
    scenes = require_scenes(repo, pid)
    flagged = [s for s in scenes if s["needs_review"]]
    c1, c2, c3 = st.columns(3)
    c1.metric("Scenes", len(scenes))
    c2.metric("Flagged for review", len(flagged))
    c3.metric("Avg. confidence", f"{100 * sum((s['confidence'] or 0) for s in scenes) / len(scenes):.0f}%")
    only_flagged = st.toggle("Show only flagged scenes", value=False, disabled=not flagged,
                             help="Saving while filtered keeps hidden scenes untouched only if you leave this off.")
    view = flagged if only_flagged else scenes
    st.caption("Edit cells, add rows (bottom of the table) or delete rows, then click Save. Lists are comma separated. "
               "Story order uses the 'Order' column (use decimals to insert a scene between two others).")
    rows = [{"id": s["id"], "seq": s["seq"], "scene_number": s["scene_number"], "heading": s["heading"], "page_ref": s["page_ref"],
             "location": s["location"], "int_ext": s["int_ext"], "time_of_day": s["time_of_day"],
             "characters": join_csv(s["characters"]), "description": s["description"], "main_action": s["main_action"],
             "has_dialogue": bool(s["has_dialogue"]), **{k: join_csv(item_names(s[k])) for k, _ in RES},
             "complexity": s["complexity"], "confidence": s["confidence"], "needs_review": bool(s["needs_review"]),
             "review_reason": s["review_reason"]} for s in view]
    df = pd.DataFrame(rows)
    cfg = {"id": None, "seq": st.column_config.NumberColumn("Order"), "scene_number": st.column_config.TextColumn("Scene #"),
           "int_ext": st.column_config.SelectboxColumn("INT/EXT", options=INT_EXT),
           "time_of_day": st.column_config.SelectboxColumn("Time", options=TIMES_OF_DAY),
           "complexity": st.column_config.SelectboxColumn("Complexity", options=COMPLEXITY),
           "confidence": st.column_config.NumberColumn("Confidence", disabled=True, format="%.2f"),
           "has_dialogue": st.column_config.CheckboxColumn("Dialogue"),
           "needs_review": st.column_config.CheckboxColumn("Review?")}
    edited = st.data_editor(df, column_config=cfg, num_rows="dynamic", hide_index=True, key=f"sceneed_{pid}_{only_flagged}", **STRETCH)
    if st.button("Save scene changes", type="primary"):
        by_id = {s["id"]: s for s in scenes}
        recs = []
        for r in edited.to_dict("records"):
            old = by_id.get(r.get("id")) if r.get("id") == r.get("id") and r.get("id") is not None else None
            rec = dict(r)
            rec["characters"] = split_csv(r.get("characters"))
            for k, _ in RES:
                rec[k] = names_to_items(r.get(k), (old or {}).get(k, []))
            recs.append(rec)
        if only_flagged:  # keep scenes hidden by the filter exactly as they are
            shown = {r["id"] for r in view}
            recs += [{"id": s["id"]} for s in scenes if s["id"] not in shown]
        try:
            repo.sync_scenes(pid, recs)
            production_planner.rebuild_registers(repo, pid)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not save scenes: {exc}")
        else:
            flash("success", "Scenes saved; characters, locations and resources were refreshed (your register edits are kept).")
            st.rerun()

    st.divider()
    st.subheader("Re-analyse one scene with AI")
    labels = {f"Sc {s['scene_number']} - {s['heading']}": s["id"] for s in scenes}
    pick = st.selectbox("Scene", list(labels))
    if st.button("Re-analyse selected scene", disabled=not has_api_key()):
        with st.spinner("Asking the model..."):
            scene = repo.get_scene(labels[pick])
            known = [c["name"] for c in repo.list_characters(pid)]
            res = safe(scene_extractor.reanalyze_scene, get_client(), scene, known)
            if res:
                st.session_state["redo"] = (labels[pick], res)
    redo = st.session_state.get("redo")
    if redo and redo[0] == labels[pick]:
        st.write("Proposed update (not saved yet):")
        st.json({k: (join_csv(item_names(v)) if isinstance(v, list) and v and isinstance(v[0], dict) else v)
                 for k, v in redo[1].items() if k != "evidence"})
        if st.button("Apply proposed update", type="primary"):
            repo.update_scene_fields(redo[0], redo[1])
            production_planner.rebuild_registers(repo, pid)
            st.session_state.pop("redo")
            st.rerun()
