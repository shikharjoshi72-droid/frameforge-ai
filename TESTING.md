# 🧪 Testing & Verification Report

This document outlines the testing coverage, verified functionality, integration checks, and remaining validation requirements for the project.

The testing process focused on code reliability, data integrity, error handling, PDF generation, scheduling logic, and end-to-end pipeline behaviour.

## 1. Testing Environment

| Component | Environment / Status |
|---|---|
| Python | 3.12 |
| Operating Environment | Offline sandbox |
| Streamlit | Not installed |
| OpenAI SDK | Not installed |
| Pydantic | Not installed |
| PyMuPDF | Not installed |
| Database | SQLite (real database used during smoke testing) |
| External AI API | NVIDIA API (not live-tested) |

**Environment limitation:** The sandbox did not have internet access. Consequently, `streamlit`, `openai`, `pydantic`, and `pymupdf` could not be installed. Tests requiring these dependencies were either simulated using controlled test doubles or left for local verification.

## 2. Automated Test Results

<details>
<summary><strong>Test Summary — 23 Passed, 0 Failed</strong></summary>

| Metric | Result |
|---|---:|
| Total automated tests | 23 |
| Passed | 23 |
| Failed | 0 |
| Pass rate | 100% |

**Command executed:**

```bash
python -m tests.run_all
```

</details>

<details>
<summary><strong>2.1 Screenplay Heading Parser & Scene Segmentation</strong></summary>

Verified functionality:

- INT., EXT., and INT./EXT. heading recognition.
- Numbered scene headings.
- Informal lowercase scene headings.
- `SCENE n` format recognition.
- Time-of-day extraction and mapping.
- Prevention of ordinary prose being incorrectly identified as a scene heading.
- Correct scene ordering and numbering.
- Handling of a 30-scene screenplay without losing scene count or order.
- Title page exclusion during scene extraction.
- Detection and reporting of scripts without recognizable scene headings.

</details>

<details>
<summary><strong>2.2 Text Chunking & Context Preservation</strong></summary>

Verified functionality:

- Original text ordering is preserved.
- Context overlap between consecutive chunks.
- Oversized scenes are split into smaller chunks.
- No text is lost during oversized scene splitting.
- Chunk boundaries preserve the screenplay's logical structure.

</details>

<details>
<summary><strong>2.3 Dialogue & Character Cue Detection</strong></summary>

Verified functionality:

- Character speaker identification.
- Voice-over (V.O.) separation.
- Recognition of dialogue-related cues.
- Transition instructions are not incorrectly identified as characters.
- Off-screen (O.S.) voices are not treated as physically present characters.

</details>

<details>
<summary><strong>2.4 Text Cleaning & Normalization</strong></summary>

Verified functionality:

- Removal of unnecessary page numbers.
- Removal of `(CONTINUED)` markers.
- Basic screenplay text normalization.
- Preservation of meaningful screenplay content.

</details>

<details>
<summary><strong>2.5 JSON Parsing & Repair</strong></summary>

Verified recovery and error-handling scenarios:

- Markdown code-fence removal.
- Removal of `<think>` blocks.
- Trailing comma correction.
- Recovery from truncated JSON output.
- Handling of explanatory text surrounding JSON.
- Invalid or completely malformed output correctly raises an error.

</details>

<details>
<summary><strong>2.6 Document Loader & Input Validation</strong></summary>

Verified functionality:

- TXT document loading.
- DOCX document loading.
- Text-based PDF loading using the `pypdf` fallback.
- Scanned PDF rejection with an appropriate OCR-related error message.
- Unsupported file type rejection.
- Empty document detection.
- Oversized file rejection.

**Note:** The PyMuPDF-specific extraction path was not tested.

</details>

<details>
<summary><strong>2.7 Production Scheduling Engine</strong></summary>

Verified functionality:

- Deterministic scheduling.
- Every scene scheduled exactly once.
- Day and night scenes are never mixed.
- Production capacity constraints are respected.
- Weekend skipping.
- Pending production dates.
- Availability conflict detection.
- Consistent scheduling results for identical inputs.

</details>

<details>
<summary><strong>2.8 End-to-End Pipeline Integration</strong></summary>

The complete pipeline was exercised using a test double in place of the live NVIDIA API.

Verified functionality:

- Scene extraction and numbering.
- Removal and flagging of hallucinated characters.
- Dropped content blocks are flagged instead of being automatically invented.
- O.S. voices are not incorrectly classified as physically present.
- Generic equipment entries are filtered.
- Counts are calculated using Python rather than relying on AI-generated totals.
- Failed chunks are preserved and can be retried.
- Database persistence across newly initialized Repository instances.
- User modifications survive register rebuilds.
- Production schedule saving and approval.
- Black Book generation and verification.

**Black Book verification:**

- Generated a 17-page PDF.
- Extracted the generated PDF's text.
- Verified that all expected sections were present.

</details>

## 3. Additional Integration & Visual Checks

Beyond the 23 automated tests, additional manual and smoke-testing activities were performed.

### PDF Visual Verification

Rendered PDF pages were visually inspected for:

- Cover page layout.
- Table of contents.
- Table formatting.
- Repeating table headers across pages.
- General document readability and layout consistency.

### Streamlit UI Smoke Testing

- Every UI page function was executed against a stubbed Streamlit implementation.
- Real SQLite database operations were exercised.
- Save-related code paths were tested.
- Database-backed UI workflows were checked without launching the actual browser interface.

**Important:** This verifies page-function execution and associated logic, not actual browser rendering or interactive widget behaviour.

## 4. Known Limitations & Pending Verification

The following areas remain unverified and require testing in a fully configured local environment.

| Area | Pending Verification |
|---|---|
| NVIDIA API | Live model availability, actual JSON compliance, `enable_thinking` behaviour and rate limits |
| Pydantic | Execution of schemas in `ai/schemas.py` and validation of custom validators |
| Streamlit | Actual browser rendering, layout, widget interactions and navigation |
| PyMuPDF | PDF extraction using the PyMuPDF implementation |
| Extraction Accuracy | Accuracy against manually labelled screenplay ground truth |
| Medium Screenplays | Real-model testing with 20–30 scene screenplays |
| Long Screenplays | Real-model testing with 50+ scene screenplays |

### Recommended Local Validation

**1. Verify NVIDIA API connectivity**

Navigate to:

`Settings → Test Connection`

Check model availability, API authentication, response formatting and rate-limit behaviour.

**2. Validate Pydantic schemas**

Install the required dependencies and execute the schema validation tests, particularly those defined in:

```text
ai/schemas.py
```

**3. Launch the actual Streamlit application**

Run the application locally and verify:

- Page rendering.
- Navigation.
- Input validation.
- Widget interactions.
- Database save and retrieval workflows.

**4. Test PDF extraction**

Install PyMuPDF and compare its extraction output with the existing `pypdf` fallback.

**5. Measure extraction accuracy**

Prepare a manually labelled dataset of 10–20 screenplay scenes.

Compare the application's extracted scenes, character names, dialogue cues and scene metadata against the manually verified results.

Report precision, recall and other relevant metrics only after completing this evaluation.

**6. Perform real-world screenplay testing**

Test the live AI integration with:

- Short screenplays.
- Medium screenplays (20–30 scenes).
- Long screenplays (50+ scenes).

Pay particular attention to scene consistency, missing content, character identification, JSON reliability and processing failures.

## 5. Final Assessment

The project has successfully completed its available offline automated test suite, with **23 passing tests and zero reported failures**.

Core parsing, segmentation, chunking, dialogue detection, text cleaning, JSON repair, document loading through the tested fallback, scheduling, SQLite persistence, and PDF generation workflows have been verified within the stated testing environment.

Additional smoke tests and PDF visual checks were also completed.

However, passing offline tests does not establish that the live NVIDIA integration, Pydantic schemas, or actual Streamlit browser interface are fully functional. These require validation in the intended local environment.

**Testing Status:** Offline automated tests passed. Live integration and production-environment validation remain pending.

---

*This report reflects the tests actually performed and deliberately distinguishes verified functionality from simulated and unverified behaviour.*
