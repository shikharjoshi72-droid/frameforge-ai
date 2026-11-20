"""All SQL lives here. UI and core modules talk to this class only."""
import uuid
from datetime import date

from core.utils import clean, jdump, jload, now
from database.db import DatabaseError, init_db, session

SCENE_JSON = {"characters": "characters_json", "mentioned": "mentioned_json", "props": "props_json",
              "costumes": "costumes_json", "vehicles": "vehicles_json", "special_effects": "effects_json",
              "equipment": "equipment_json"}
SCENE_PLAIN = ["scene_uid", "seq", "scene_number", "heading", "page_ref", "location", "int_ext", "time_of_day",
               "description", "main_action", "has_dialogue", "complexity", "confidence", "evidence",
               "needs_review", "review_reason", "raw_text", "source"]
SCENE_EDITABLE = ["seq", "scene_number", "heading", "page_ref", "location", "int_ext", "time_of_day",
                  "description", "main_action", "has_dialogue", "complexity", "needs_review", "review_reason"]
CHAR_COLS = ["name", "description", "char_type", "role", "first_scene", "last_scene", "appearances",
             "relationships", "costume_notes", "notes"]
LOC_COLS = ["name", "description", "int_ext", "day_night", "scene_numbers", "props", "complexity", "notes",
            "duplicate_hint"]
RES_COLS = ["name", "category", "scene_uids", "source_type", "description", "quantity", "notes", "manual"]


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


class Repository:
    def __init__(self, path=None):
        self.path = path
        init_db(path)

    # ---- low-level helpers ----
    def _all(self, sql, params=()):
        with session(self.path) as c:
            return _rows(c.execute(sql, params))

    def _one(self, sql, params=()):
        rows = self._all(sql, params)
        return rows[0] if rows else None

    def _exec(self, sql, params=()):
        with session(self.path) as c:
            return c.execute(sql, params).lastrowid

    # ---- projects ----
    def create_project(self, title, company="", director="", genre="", target_runtime=None, start_date=None,
                       description="") -> str:
        pid = "FF-" + uuid.uuid4().hex[:8].upper()
        ts = now()
        self._exec("INSERT INTO projects(id,title,company,director,genre,target_runtime,start_date,description,"
                   "created_at,updated_at,last_opened_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (pid, title.strip(), company, director, genre, target_runtime, start_date, description, ts, ts, ts))
        return pid

    def list_projects(self):
        return self._all("SELECT * FROM projects ORDER BY COALESCE(last_opened_at, created_at) DESC")

    def get_project(self, pid):
        return self._one("SELECT * FROM projects WHERE id=?", (pid,))

    def update_project(self, pid, **fields):
        allowed = {"title", "company", "director", "genre", "target_runtime", "start_date", "description",
                   "notes", "review_status", "bb_version", "schedule_approved"}
        keys = [k for k in fields if k in allowed]
        if not keys:
            return
        sets = ",".join(f"{k}=?" for k in keys)
        self._exec(f"UPDATE projects SET {sets}, updated_at=? WHERE id=?",
                   [clean(fields[k]) for k in keys] + [now(), pid])

    def touch_project(self, pid):
        self._exec("UPDATE projects SET last_opened_at=? WHERE id=?", (now(), pid))

    def delete_project(self, pid):
        self._exec("DELETE FROM projects WHERE id=?", (pid,))

    # ---- documents ----
    def add_document(self, pid, kind, filename, sha256, size_bytes, page_count, stored_path, text="", pages=None,
                     warnings=None):
        return self._exec(
            "INSERT INTO documents(project_id,kind,filename,sha256,size_bytes,page_count,stored_path,"
            "extracted_text,pages_json,warnings_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (pid, kind, filename, sha256, size_bytes, page_count, stored_path, text, jdump(pages or []),
             jdump(warnings or []), now()))

    def find_document_by_hash(self, pid, sha256):
        return self._one("SELECT id,filename,created_at FROM documents WHERE project_id=? AND sha256=? "
                         "AND kind='screenplay'", (pid, sha256))

    def latest_document(self, pid, kind="screenplay"):
        d = self._one("SELECT * FROM documents WHERE project_id=? AND kind=? ORDER BY id DESC LIMIT 1", (pid, kind))
        if d:
            d["pages"] = jload(d.get("pages_json"), [])
            d["warnings"] = jload(d.get("warnings_json"), [])
        return d

    def list_documents_by_kind(self, pid, kind):
        return self._all("SELECT id,filename,page_count,stored_path,created_at FROM documents WHERE project_id=? "
                         "AND kind=? ORDER BY id DESC", (pid, kind))

    # ---- analysis + stage status + chunks ----
    def save_analysis(self, pid, data: dict, model=""):
        self._exec("INSERT INTO analyses(project_id,data_json,model,updated_at) VALUES(?,?,?,?) "
                   "ON CONFLICT(project_id) DO UPDATE SET data_json=excluded.data_json, model=excluded.model, "
                   "updated_at=excluded.updated_at", (pid, jdump(data), model, now()))

    def get_analysis(self, pid) -> dict:
        r = self._one("SELECT data_json FROM analyses WHERE project_id=?", (pid,))
        return jload(r["data_json"], {}) if r else {}

    def update_analysis(self, pid, **fields):
        data = self.get_analysis(pid)
        data.update(fields)
        self.save_analysis(pid, data)

    def set_stage(self, pid, stage, status, message=""):
        self._exec("INSERT INTO stage_status(project_id,stage,status,message,updated_at) VALUES(?,?,?,?,?) "
                   "ON CONFLICT(project_id,stage) DO UPDATE SET status=excluded.status, message=excluded.message, "
                   "updated_at=excluded.updated_at", (pid, stage, status, message, now()))

    def get_stages(self, pid) -> dict:
        return {r["stage"]: r for r in self._all("SELECT * FROM stage_status WHERE project_id=?", (pid,))}

    def reset_chunks(self, pid, payloads: list):
        with session(self.path) as c:
            c.execute("DELETE FROM chunk_results WHERE project_id=?", (pid,))
            for p in payloads:
                c.execute("INSERT INTO chunk_results(project_id,chunk_id,idx,status,payload_json,updated_at) "
                          "VALUES(?,?,?,?,?,?)", (pid, p["chunk_id"], p["index"], "PENDING", jdump(p), now()))

    def list_chunks(self, pid):
        rows = self._all("SELECT * FROM chunk_results WHERE project_id=? ORDER BY idx", (pid,))
        for r in rows:
            r["payload"] = jload(r["payload_json"], {})
            r["result"] = jload(r["result_json"], None)
        return rows

    def set_chunk(self, pid, chunk_id, status, result=None, error=""):
        self._exec("UPDATE chunk_results SET status=?, result_json=?, error=?, attempts=attempts+1, updated_at=? "
                   "WHERE project_id=? AND chunk_id=?",
                   (status, jdump(result) if result is not None else None, error, now(), pid, chunk_id))

    # ---- scenes ----
    def _scene_out(self, r):
        for k, col in SCENE_JSON.items():
            r[k] = jload(r.pop(col), [])
        r["status"] = r.get("status") or "Not Started"
        return r

    def list_scenes(self, pid, with_raw=False):
        rows = self._all("SELECT s.*, COALESCE(p.status,'Not Started') AS status FROM scenes s "
                         "LEFT JOIN progress p ON p.scene_id=s.id WHERE s.project_id=? ORDER BY s.seq, s.id", (pid,))
        out = [self._scene_out(r) for r in rows]
        if not with_raw:
            for r in out:
                r.pop("raw_text", None)
        return out

    def get_scene(self, scene_id):
        r = self._one("SELECT s.*, COALESCE(p.status,'Not Started') AS status FROM scenes s "
                      "LEFT JOIN progress p ON p.scene_id=s.id WHERE s.id=?", (scene_id,))
        return self._scene_out(r) if r else None

    def _scene_values(self, s):
        vals = [clean(s.get(k)) for k in SCENE_PLAIN]
        for k in SCENE_JSON:
            vals.append(jdump(s.get(k) or []))
        return vals

    def replace_scenes(self, pid, scenes: list):
        """Replace all scenes (cascades schedule/progress). Used after a full analysis."""
        cols = SCENE_PLAIN + list(SCENE_JSON.values())
        with session(self.path) as c:
            c.execute("DELETE FROM scenes WHERE project_id=?", (pid,))
            c.execute("DELETE FROM shooting_days WHERE project_id=?", (pid,))
            for s in scenes:
                cur = c.execute(f"INSERT INTO scenes(project_id,{','.join(cols)}) VALUES(?,{','.join('?' * len(cols))})",
                                [pid] + self._scene_values(s))
                c.execute("INSERT INTO progress(scene_id,project_id,status,updated_at) VALUES(?,?,?,?)",
                          (cur.lastrowid, pid, "Not Started", now()))
            c.execute("UPDATE projects SET schedule_approved=0, updated_at=? WHERE id=?", (now(), pid))

    def sync_scenes(self, pid, records: list):
        """Apply editor output: update existing, insert new, delete removed."""
        existing = {r["id"]: r for r in self._all("SELECT id FROM scenes WHERE project_id=?", (pid,))}
        kept = set()
        with session(self.path) as c:
            nxt = (c.execute("SELECT COALESCE(MAX(seq),0) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]) + 1
            for rec in records:
                rid = clean(rec.get("id"))
                rid = int(rid) if rid is not None else None
                js = {col: jdump(rec.get(k) or []) for k, col in SCENE_JSON.items() if k in rec}
                if rid in existing:
                    kept.add(rid)
                    cols = [k for k in SCENE_EDITABLE if k in rec]
                    sets = [f"{k}=?" for k in cols] + [f"{k}=?" for k in js]
                    vals = [clean(rec.get(k)) for k in cols] + list(js.values())
                    if sets:
                        c.execute(f"UPDATE scenes SET {','.join(sets)} WHERE id=?", vals + [rid])
                else:
                    data = {k: clean(rec.get(k)) for k in SCENE_EDITABLE}
                    data["seq"] = data["seq"] if data["seq"] is not None else nxt
                    nxt += 1
                    data["scene_uid"] = "U" + uuid.uuid4().hex[:5].upper()
                    data["source"] = "USER"
                    data["confidence"] = 1.0
                    cols = list(data)
                    all_cols = cols + [col for col in SCENE_JSON.values()]
                    vals = [data[k] for k in cols] + [js.get(col, "[]") for col in SCENE_JSON.values()]
                    cur = c.execute(f"INSERT INTO scenes(project_id,{','.join(all_cols)}) "
                                    f"VALUES(?,{','.join('?' * len(all_cols))})", [pid] + vals)
                    c.execute("INSERT INTO progress(scene_id,project_id,status,updated_at) VALUES(?,?,?,?)",
                              (cur.lastrowid, pid, "Not Started", now()))
            for rid in set(existing) - kept:
                c.execute("DELETE FROM scenes WHERE id=?", (rid,))

    def update_scene_fields(self, scene_id, fields: dict):
        sets, vals = [], []
        for k, v in fields.items():
            if k in SCENE_JSON:
                sets.append(f"{SCENE_JSON[k]}=?")
                vals.append(jdump(v or []))
            elif k in SCENE_PLAIN:
                sets.append(f"{k}=?")
                vals.append(clean(v))
        if sets:
            self._exec(f"UPDATE scenes SET {','.join(sets)} WHERE id=?", vals + [scene_id])

    # ---- generic register sync (characters / locations / resources) ----
    def _sync(self, table, cols, pid, records, defaults=None):
        existing = {r["id"] for r in self._all(f"SELECT id FROM {table} WHERE project_id=?", (pid,))}
        kept = set()
        with session(self.path) as c:
            for rec in records:
                rid = clean(rec.get("id"))
                rid = int(rid) if rid is not None else None
                vals = [clean(rec.get(k, (defaults or {}).get(k))) for k in cols]
                vals = [int(v) if isinstance(v, bool) else v for v in vals]
                if rid in existing:
                    kept.add(rid)
                    c.execute(f"UPDATE {table} SET {','.join(k + '=?' for k in cols)} WHERE id=?", vals + [rid])
                else:
                    c.execute(f"INSERT INTO {table}(project_id,{','.join(cols)}) VALUES(?,{','.join('?' * len(cols))})",
                              [pid] + vals)
            for rid in existing - kept:
                c.execute(f"DELETE FROM {table} WHERE id=?", (rid,))

    def sync_characters(self, pid, recs):
        self._sync("characters", CHAR_COLS, pid, recs)

    def sync_locations(self, pid, recs):
        self._sync("locations", LOC_COLS, pid, recs)

    def sync_resources(self, pid, recs):
        self._sync("resources", RES_COLS, pid, recs, {"manual": 0})

    def list_characters(self, pid):
        return self._all("SELECT * FROM characters WHERE project_id=? ORDER BY appearances DESC, name", (pid,))

    def list_locations(self, pid):
        return self._all("SELECT * FROM locations WHERE project_id=? ORDER BY name", (pid,))

    def list_resources(self, pid, category=None):
        if category:
            return self._all("SELECT * FROM resources WHERE project_id=? AND category=? ORDER BY name", (pid, category))
        return self._all("SELECT * FROM resources WHERE project_id=? ORDER BY category, name", (pid,))

    def link_scene_characters(self, pid):
        """Rebuild scene_characters from scene data (names matched case-insensitively)."""
        from core.utils import norm_character
        chars = {norm_character(c["name"]): c["id"] for c in self.list_characters(pid)}
        with session(self.path) as c:
            c.execute("DELETE FROM scene_characters WHERE scene_id IN (SELECT id FROM scenes WHERE project_id=?)", (pid,))
            for s in self.list_scenes(pid):
                for n in s["characters"]:
                    cid = chars.get(norm_character(n))
                    if cid:
                        c.execute("INSERT OR IGNORE INTO scene_characters VALUES(?,?)", (s["id"], cid))

    # ---- schedule ----
    def save_schedule(self, pid, days: list):
        """days: [{day_number, shoot_date, call_type, est_minutes, location_names, explanation, scene_ids:[...] }]"""
        with session(self.path) as c:
            c.execute("DELETE FROM shooting_days WHERE project_id=?", (pid,))
            for d in days:
                cur = c.execute("INSERT INTO shooting_days(project_id,day_number,shoot_date,call_type,est_minutes,"
                                "location_names,explanation) VALUES(?,?,?,?,?,?,?)",
                                (pid, d["day_number"], d.get("shoot_date"), d.get("call_type"), d.get("est_minutes"),
                                 d.get("location_names"), d.get("explanation")))
                for pos, (sid, mins) in enumerate(zip(d["scene_ids"], d.get("scene_minutes") or [None] * len(d["scene_ids"]))):
                    c.execute("INSERT INTO schedule_items(day_id,project_id,scene_id,position,est_minutes) "
                              "VALUES(?,?,?,?,?)", (cur.lastrowid, pid, sid, pos, mins))
            c.execute("UPDATE projects SET schedule_approved=0, updated_at=? WHERE id=?", (now(), pid))

    def list_shooting_days(self, pid):
        days = self._all("SELECT * FROM shooting_days WHERE project_id=? ORDER BY day_number", (pid,))
        scenes = {s["id"]: s for s in self.list_scenes(pid)}
        for d in days:
            items = self._all("SELECT * FROM schedule_items WHERE day_id=? ORDER BY position", (d["id"],))
            d["scene_ids"] = [i["scene_id"] for i in items if i["scene_id"] in scenes]
            d["scenes"] = [scenes[i] for i in d["scene_ids"]]
        return days

    def update_day(self, day_id, **fields):
        allowed = {"shoot_date", "call_type", "completed", "explanation", "location_names", "est_minutes"}
        keys = [k for k in fields if k in allowed]
        if keys:
            self._exec(f"UPDATE shooting_days SET {','.join(k + '=?' for k in keys)} WHERE id=?",
                       [clean(fields[k]) for k in keys] + [day_id])

    def move_scene_to_day(self, scene_id, day_id):
        with session(self.path) as c:
            c.execute("DELETE FROM schedule_items WHERE scene_id=?", (scene_id,))
            if day_id is not None:
                pid = c.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()[0]
                pos = c.execute("SELECT COALESCE(MAX(position),-1)+1 FROM schedule_items WHERE day_id=?",
                                (day_id,)).fetchone()[0]
                c.execute("INSERT INTO schedule_items(day_id,project_id,scene_id,position) VALUES(?,?,?,?)",
                          (day_id, pid, scene_id, pos))

    def set_schedule_approved(self, pid, approved: bool):
        self.update_project(pid, schedule_approved=int(approved))

    # ---- call sheets ----
    def save_call_sheet(self, pid, day_id, **f):
        self._exec("INSERT INTO call_sheets(project_id,day_id,call_time,wrap_time,crew,emergency_contact,"
                   "instructions,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(day_id) DO UPDATE SET "
                   "call_time=excluded.call_time, wrap_time=excluded.wrap_time, crew=excluded.crew, "
                   "emergency_contact=excluded.emergency_contact, instructions=excluded.instructions, "
                   "updated_at=excluded.updated_at",
                   (pid, day_id, f.get("call_time", ""), f.get("wrap_time", ""), f.get("crew", ""),
                    f.get("emergency_contact", ""), f.get("instructions", ""), now()))

    def get_call_sheet(self, day_id):
        return self._one("SELECT * FROM call_sheets WHERE day_id=?", (day_id,)) or {}

    # ---- progress ----
    def set_scene_status(self, scene_id, status):
        self._exec("UPDATE progress SET status=?, updated_at=? WHERE scene_id=?", (status, now(), scene_id))

    def status_counts(self, pid) -> dict:
        rows = self._all("SELECT status, COUNT(*) n FROM progress WHERE project_id=? GROUP BY status", (pid,))
        return {r["status"]: r["n"] for r in rows}

    # ---- stats ----
    def dashboard_stats(self) -> dict:
        one = lambda sql: (self._one(sql) or {"n": 0})["n"]
        total_scenes = one("SELECT COUNT(*) n FROM scenes")
        done = one("SELECT COUNT(*) n FROM progress WHERE status='Completed'")
        return {
            "projects": one("SELECT COUNT(*) n FROM projects"),
            "analysed": one("SELECT COUNT(DISTINCT project_id) n FROM scenes"),
            "scenes": total_scenes,
            "characters": one("SELECT COUNT(*) n FROM characters"),
            "locations": one("SELECT COUNT(*) n FROM locations"),
            "completion": round(100 * done / total_scenes, 1) if total_scenes else 0.0,
        }

    def upcoming_days(self, limit=6):
        today = date.today().isoformat()
        return self._all(
            "SELECT d.*, p.title FROM shooting_days d JOIN projects p ON p.id=d.project_id "
            "WHERE d.completed=0 AND d.shoot_date IS NOT NULL AND d.shoot_date>=? "
            "ORDER BY d.shoot_date LIMIT ?", (today, limit))
