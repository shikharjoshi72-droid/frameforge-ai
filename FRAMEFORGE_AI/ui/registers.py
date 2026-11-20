"""Character, Location and Production Resource registers (all editable)."""
import pandas as pd
import streamlit as st

from config.constants import COMPLEXITY, RESOURCE_CATEGORIES, SOURCE_TYPES
from core import production_planner
from ui import theme
from ui.common import STRETCH, flash, require_project, require_scenes


def _rebuild_button(repo, pid):
    if st.button("Rebuild from scenes", help="Re-derive this register from current scenes. Your manual edits are kept."):
        production_planner.rebuild_registers(repo, pid)
        flash("success", "Registers rebuilt from scene data.")
        st.rerun()


def render_characters(repo, pid):
    st.title("Character Register")
    require_project(repo, pid)
    require_scenes(repo, pid)
    chars = repo.list_characters(pid)
    st.caption("Appearance counts, first and last scenes are computed in Python from validated scene data, not by the AI. "
               "Role is derived from scene share (>=25% Main, >=8% Supporting).")
    df = pd.DataFrame([{k: c[k] for k in ["id", "name", "description", "char_type", "role", "first_scene", "last_scene",
                                          "appearances", "relationships", "costume_notes", "notes"]} for c in chars])
    cfg = {"id": None, "first_scene": st.column_config.TextColumn("First scene", disabled=True),
           "last_scene": st.column_config.TextColumn("Last scene", disabled=True),
           "appearances": st.column_config.NumberColumn("Appearances", disabled=True)}
    edited = st.data_editor(df, column_config=cfg, num_rows="dynamic", hide_index=True, key=f"chars_{pid}", **STRETCH)
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("Save characters", type="primary"):
        repo.sync_characters(pid, edited.to_dict("records"))
        repo.link_scene_characters(pid)
        flash("success", "Characters saved.")
        st.rerun()
    with c2:
        _rebuild_button(repo, pid)
    if chars:
        sel = st.selectbox("Associated scenes for", [c["name"] for c in chars])
        scenes = [s for s in repo.list_scenes(pid) if sel.upper() in [x.upper() for x in s["characters"]]]
        st.write(", ".join(f"Sc {s['scene_number']}" for s in scenes) or "None")


def render_locations(repo, pid):
    st.title("Locations")
    require_project(repo, pid)
    require_scenes(repo, pid)
    locs = repo.list_locations(pid)
    dups = [l for l in locs if l["duplicate_hint"]]
    if dups:
        with st.expander(f"{len(dups)} location(s) may be duplicates - review", expanded=True):
            st.caption("Locations are only merged when names match exactly. To merge look-alikes, correct the location in "
                       "Scene Breakdown and rebuild.")
            for l in dups:
                st.markdown(f"- **{l['name']}**: {l['duplicate_hint']}")
    df = pd.DataFrame([{k: l[k] for k in ["id", "name", "description", "int_ext", "day_night", "scene_numbers", "props",
                                          "complexity", "notes", "duplicate_hint"]} for l in locs])
    cfg = {"id": None, "complexity": st.column_config.SelectboxColumn("Complexity", options=COMPLEXITY),
           "scene_numbers": st.column_config.TextColumn("Scenes", disabled=True),
           "duplicate_hint": st.column_config.TextColumn("Duplicate hint", disabled=True)}
    edited = st.data_editor(df, column_config=cfg, num_rows="dynamic", hide_index=True, key=f"locs_{pid}", **STRETCH)
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("Save locations", type="primary"):
        repo.sync_locations(pid, edited.to_dict("records"))
        flash("success", "Locations saved.")
        st.rerun()
    with c2:
        _rebuild_button(repo, pid)


def render_resources(repo, pid):
    st.title("Production Resources")
    require_project(repo, pid)
    require_scenes(repo, pid)
    st.caption("Source type: EXPLICIT = named in the screenplay, INFERRED = implied by the action, RECOMMENDED = AI suggestion. "
               "Rows you edit or add are kept when registers are rebuilt.")
    all_rows = repo.list_resources(pid)
    tabs = st.tabs(RESOURCE_CATEGORIES)
    for cat, tab in zip(RESOURCE_CATEGORIES, tabs):
        with tab:
            rows = [r for r in all_rows if r["category"] == cat]
            cols = ["id", "name", "scene_uids", "source_type", "description", "quantity", "notes"]
            df = pd.DataFrame([{k: r[k] for k in cols} for r in rows], columns=cols)
            cfg = {"id": None, "scene_uids": st.column_config.TextColumn("Scenes"),
                   "source_type": st.column_config.SelectboxColumn("Source", options=SOURCE_TYPES, default="EXPLICIT")}
            edited = st.data_editor(df, column_config=cfg, num_rows="dynamic", hide_index=True, key=f"res_{pid}_{cat}", **STRETCH)
            if st.button(f"Save {cat.lower()} register", key=f"save_{cat}", type="primary"):
                orig = {r["id"]: r for r in rows}
                out = [r for r in all_rows if r["category"] != cat]
                for rec in edited.to_dict("records"):
                    rid = rec.get("id")
                    o = orig.get(rid) if rid == rid and rid is not None else None
                    changed = o is None or any((o[k] or "") != (rec.get(k) or "") for k in cols[1:] if rec.get(k) == rec.get(k))
                    rec["category"] = cat
                    rec["manual"] = 1 if changed else (o["manual"] if o else 1)
                    if not rec.get("source_type") or rec["source_type"] != rec["source_type"]:
                        rec["source_type"] = "EXPLICIT"
                    out.append(rec)
                repo.sync_resources(pid, out)
                flash("success", f"{cat} register saved.")
                st.rerun()
