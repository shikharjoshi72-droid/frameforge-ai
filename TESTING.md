# Testing report (honest status)

Environment used: Python 3.12, sandbox **without internet**. `streamlit`, `openai`, `pydantic` and `pymupdf` could **not** be installed there.

## Automated tests: 23 passed, 0 failed (`python -m tests.run_all`)
| Area | What is verified |
|---|---|
| Heading parser/segmentation | INT/EXT/I-E, numbered headings, informal lowercase headings, `SCENE n`, time-of-day mapping, prose not mistaken for headings, 30-scene script keeps count/order, title page skipped, no-heading scripts flagged |
| Chunking | order preserved, context overlap, oversized scene split without losing text |
| Dialogue cues | speakers detected, V.O. separated, transitions ignored |
| Text cleaning | page numbers / (CONTINUED) removed |
| JSON repair | fences, `<think>` blocks, trailing commas, truncated output, surrounding prose, garbage -> error |
| Loader | TXT, DOCX, text PDF (pypdf fallback), scanned PDF rejected with OCR message, bad type / empty / oversize |
| Scheduler | deterministic, every scene scheduled once, day/night never mixed, capacity respected, weekend skipping, pending dates, availability conflicts |
| Pipeline (end to end, **with a test double instead of the NVIDIA API**) | scenes/numbering, hallucinated character removed + flagged, dropped block flagged not invented, O.S. voice not "present", generic equipment filtered, Python-computed counts, failed chunk preserved + retry, DB persistence across a new Repository, user edits survive register rebuild, schedule save/approve, 17-page Black Book generated and verified (all sections found by text extraction), progress metrics |

Also done: a visual check of rendered PDF pages (cover, contents, tables with repeating headers), and a smoke run executing every UI page function and save path against a real SQLite DB with a stubbed Streamlit.

## NOT verified (do these on your machine first)
1. **Live NVIDIA calls**: model ID availability, real JSON compliance, `enable_thinking` handling, rate limits. Start with Settings > Test connection.
2. **Pydantic schemas** (`ai/schemas.py`) were never executed (pydantic missing in the sandbox); expect to fix small validator issues if any.
3. **Streamlit rendering**: pages were exercised with a stub, not in a browser. Layout/widget behaviour is untested.
4. **PyMuPDF** extraction path (the pypdf fallback was tested).
5. **Extraction accuracy**: no manually verified ground truth exists yet, so no accuracy number is reported. Suggested next step: hand-label 10-20 scenes and compare.
6. Medium (20-30 scene) and long (50+) *real* screenplays through the real model.
