"""SQLite schema. Lists are stored as JSON text; relations use real foreign keys."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT, director TEXT, genre TEXT,
  target_runtime INTEGER, start_date TEXT, description TEXT, notes TEXT DEFAULT '',
  review_status TEXT DEFAULT 'DRAFT', bb_version INTEGER DEFAULT 0,
  schedule_approved INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT, last_opened_at TEXT
);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, filename TEXT, sha256 TEXT, size_bytes INTEGER, page_count INTEGER,
  stored_path TEXT, extracted_text TEXT, pages_json TEXT, warnings_json TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS analyses (
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  data_json TEXT, model TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS chunk_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chunk_id TEXT NOT NULL, idx INTEGER, status TEXT DEFAULT 'PENDING',
  payload_json TEXT, result_json TEXT, error TEXT, attempts INTEGER DEFAULT 0, updated_at TEXT,
  UNIQUE(project_id, chunk_id)
);
CREATE TABLE IF NOT EXISTS scenes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  scene_uid TEXT, seq REAL, scene_number TEXT, heading TEXT, page_ref TEXT, location TEXT,
  int_ext TEXT, time_of_day TEXT, description TEXT, main_action TEXT, has_dialogue INTEGER DEFAULT 0,
  characters_json TEXT DEFAULT '[]', mentioned_json TEXT DEFAULT '[]', props_json TEXT DEFAULT '[]',
  costumes_json TEXT DEFAULT '[]', vehicles_json TEXT DEFAULT '[]', effects_json TEXT DEFAULT '[]',
  equipment_json TEXT DEFAULT '[]', complexity TEXT, confidence REAL, evidence TEXT,
  needs_review INTEGER DEFAULT 0, review_reason TEXT, raw_text TEXT, source TEXT DEFAULT 'AI'
);
CREATE TABLE IF NOT EXISTS characters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT, description TEXT, char_type TEXT, role TEXT, first_scene TEXT, last_scene TEXT,
  appearances INTEGER DEFAULT 0, relationships TEXT, costume_notes TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS scene_characters (
  scene_id INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  PRIMARY KEY (scene_id, character_id)
);
CREATE TABLE IF NOT EXISTS locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT, description TEXT, int_ext TEXT, day_night TEXT, scene_numbers TEXT, props TEXT,
  complexity TEXT, notes TEXT, duplicate_hint TEXT
);
CREATE TABLE IF NOT EXISTS resources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT, category TEXT, scene_uids TEXT, source_type TEXT, description TEXT,
  quantity TEXT, notes TEXT, manual INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS shooting_days (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  day_number INTEGER, shoot_date TEXT, call_type TEXT, est_minutes INTEGER,
  location_names TEXT, explanation TEXT, completed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS schedule_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day_id INTEGER NOT NULL REFERENCES shooting_days(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  scene_id INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
  position INTEGER, est_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS call_sheets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  day_id INTEGER NOT NULL UNIQUE REFERENCES shooting_days(id) ON DELETE CASCADE,
  call_time TEXT, wrap_time TEXT, crew TEXT, emergency_contact TEXT, instructions TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS progress (
  scene_id INTEGER PRIMARY KEY REFERENCES scenes(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'Not Started', updated_at TEXT
);
CREATE TABLE IF NOT EXISTS stage_status (
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage TEXT NOT NULL, status TEXT, message TEXT, updated_at TEXT,
  PRIMARY KEY (project_id, stage)
);
CREATE INDEX IF NOT EXISTS ix_scenes_project ON scenes(project_id, seq);
CREATE INDEX IF NOT EXISTS ix_chars_project ON characters(project_id);
CREATE INDEX IF NOT EXISTS ix_locs_project ON locations(project_id);
CREATE INDEX IF NOT EXISTS ix_res_project ON resources(project_id, category);
CREATE INDEX IF NOT EXISTS ix_docs_project ON documents(project_id, kind);
CREATE INDEX IF NOT EXISTS ix_sched_day ON schedule_items(day_id, position);
"""
