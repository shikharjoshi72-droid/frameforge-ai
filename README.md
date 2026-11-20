# FRAMEFORGE AI
**From Script to Production. One Intelligent Black Book.**
AI-powered screenplay analysis and movie production Black Book generation (Streamlit + NVIDIA NIM + SQLite + ReportLab).

## Install
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```
Edit `.env` and set `NVIDIA_API_KEY` (get one at https://build.nvidia.com). Never commit `.env`.

## Run
```bash
streamlit run app.py
```
Then open **Settings > Test connection** first. This makes a real request to the configured model and tells you immediately
whether the key and model ID work. The model is configurable (`NVIDIA_MODEL`, or a per-session override in Settings); the
default `nvidia/nemotron-3-nano-30b-a3b` is *not assumed* to be available - verify it with the test button.

## Demo (5 minutes)
1. **New Production** -> fill the title -> you land on **Script Analysis**.
2. Upload `tests/data/sample_short.txt` (7 scenes) -> *Save & extract text* -> read the preview.
3. **AI Analysis** tab -> *Analyse Script* (progress per chunk; failed chunks can be retried without losing finished ones).
4. **Scene Breakdown**: review flagged scenes, edit cells, add/delete rows, *Save*. Re-analyse a single scene if needed.
5. **Character Register / Locations / Production Resources**: edit; look-alike locations are flagged, not merged.
6. **Shooting Schedule**: generate the *proposed* schedule, move scenes between days, *Approve*.
7. **Call Sheets**: fill confirmed call/wrap times (blank = PENDING) -> download a PDF.
8. **Production Progress**: mark scenes completed (persists across restarts).
9. **Black Book**: *Generate Black Book PDF* -> download. **AI Production Assistant**: ask questions about the project.

## Architecture
```
Streamlit UI (ui/)  ->  Application layer (core/)  ->  AI layer (ai/)  ->  NVIDIA NIM API
        \                      |                            |
         \                     v                            v
          \------------>  Repository (database/repository.py) -> SQLite (data/frameforge.db)
                               \--> exports/pdf_generator.py (ReportLab) -> generated/blackbooks/
```
Pipeline: `upload -> extract -> clean -> scene segmentation (Python) -> chunking -> LLM per chunk -> JSON repair ->
Pydantic validation -> source-text cross-checks -> merge -> SQLite -> registers (Python) -> story analysis -> human review ->
schedule (Python) -> call sheets -> Black Book PDF`.

Design rules enforced in code:
- **Python decides scene boundaries** from headings; the LLM fills one record per scene block, so scene count/order/numbering are deterministic.
- The LLM never writes to the DB or PDF: `response -> JSON parse -> Pydantic -> Python checks -> DB -> review -> PDF`.
- **Cross-checks**: AI characters not found in the scene text are removed and flagged; speakers detected from dialogue cues are added; V.O./O.S. voices and merely-mentioned names are never counted as present.
- Appearance counts, first/last scene, roles, location grouping, schedule and call sheets are computed in Python.
- Resource source types: `EXPLICIT` / `INFERRED` / `RECOMMENDED`; generic gear (camera, lights, tripod...) is filtered.
- Failures never fabricate output: failed chunks stay `FAILED` with the error and a retry button; finished chunks are kept.
- Scheduling is deterministic (same input = same schedule), labelled **PROPOSED** until approved, never invents dates/availability/contacts; unknown values print as `PENDING`.

## Database (SQLite, `data/frameforge.db`)
`projects, documents, analyses, chunk_results, scenes, characters, scene_characters, locations, resources, shooting_days,
schedule_items, call_sheets, progress, stage_status` with primary/foreign keys (cascade deletes) and indexes. All SQL lives in
`database/repository.py`. Re-running a full analysis replaces scenes and therefore resets the schedule.

## Project layout
`app.py` - router/sidebar - `config/` - `core/` (loader, preprocessor, chunker, extractor, analyzers, planner, scheduler, pipeline, black book) -
`ai/` (client, prompts, schemas, parser, assistant) - `database/` - `ui/` - `exports/pdf_generator.py` - `tests/`.

## Tests
```bash
python -m tests.run_all      # dependency-free runner; `pytest` also works
```
See `TESTING.md` for exactly what is and is not verified.

## Known limitations
- **Not yet verified against the live NVIDIA API** (see TESTING.md): model availability, JSON compliance and the `enable_thinking` switch need a first real run on your machine.
- No OCR: image-only PDFs are rejected with a clear message (export a text PDF or use DOCX/TXT).
- Page numbers for TXT/DOCX without page breaks are estimated (~55 lines/page); runtime is a 1-page-per-minute rule of thumb.
- Scene heading detection covers standard `INT./EXT./I/E` and `SCENE n` styles; unusual formats are flagged for review rather than guessed.
- Location merging is intentionally conservative; duplicates are suggested, not merged.
- Extraction quality is unmeasured on real scripts - no accuracy figure is claimed.
