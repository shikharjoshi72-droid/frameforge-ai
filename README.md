# 🎬 FRAMEFORGE AI
### From Script to Production. One Intelligent Black Book.

**Transform screenplays into production-ready movie planning documents using AI-powered screenplay analysis, intelligent scene breakdowns, production scheduling, and automated Black Book generation.**

FRAMEFORGE AI is an intelligent film pre-production management system built with **Python, Streamlit, NVIDIA NIM, SQLite, and ReportLab**.

It bridges the gap between screenplay writing and actual film production by converting raw scripts into structured production information while keeping critical decisions under human control.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 📄 Script Processing | Upload and process TXT, DOCX, and text-based PDF screenplays. |
| 🧠 AI Script Analysis | Analyse screenplays using NVIDIA NIM, processing large scripts in manageable chunks. |
| 🎬 Scene Breakdown | Extract scene numbers, headings, locations, time of day, characters, and production details. |
| 👥 Character Register | Maintain character profiles, appearance counts, roles, and scene associations. |
| 📍 Location Management | Organise shooting locations and identify potential duplicate locations. |
| 🎥 Production Resources | Track equipment, props, and other production requirements. |
| 📅 Shooting Scheduler | Generate deterministic shooting schedules with capacity and day/night constraints. |
| 📋 Call Sheets | Generate PDF call sheets with confirmed production information. |
| 📊 Production Progress | Track completed scenes and monitor production progress. |
| 📕 Black Book Generator | Generate a structured, multi-section production Black Book PDF. |
| 🤖 AI Production Assistant | Ask questions about your production and screenplay. |

## 🧠 How It Works

FRAMEFORGE AI follows a structured pipeline that combines AI intelligence with deterministic Python processing.

<pre>
        SCREENPLAY UPLOAD
                │
                ▼
       TEXT EXTRACTION & CLEANING
                │
                ▼
       SCENE SEGMENTATION (PYTHON)
                │
                ▼
         CONTEXT-AWARE CHUNKING
                │
                ▼
         NVIDIA NIM AI ANALYSIS
                │
                ▼
          JSON REPAIR & VALIDATION
                │
                ▼
       SOURCE-TEXT CROSS-CHECKS
                │
                ▼
          STRUCTURED DATABASE
                │
                ▼
       PRODUCTION REGISTERS
                │
                ▼
        SHOOTING SCHEDULER
                │
                ▼
           CALL SHEETS
                │
                ▼
       PRODUCTION BLACK BOOK
</pre>

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Core application logic and processing |
| Streamlit | Interactive web interface |
| NVIDIA NIM | AI-powered screenplay analysis |
| SQLite | Persistent project and production data |
| ReportLab | PDF and Black Book generation |
| Pydantic | Structured AI response validation |
| PyMuPDF / pypdf | PDF text extraction |
| python-docx | DOCX document processing |

## 🏗️ Architecture

```text
                 FRAMEFORGE AI
                       │
                 STREAMLIT UI
                    (ui/)
                       │
                       ▼
              APPLICATION LAYER
                   (core/)
                       │
             ┌─────────┴──────────┐
             ▼                    ▼
         AI LAYER              DATABASE
           (ai/)             (repository.py)
             │                    │
             ▼                    ▼
        NVIDIA NIM             SQLite
             │               (frameforge.db)
             │                    │
             └─────────┬──────────┘
                       │
                       ▼
                PDF GENERATOR
                 (ReportLab)
                       │
                       ▼
              GENERATED BLACK BOOKS
```

### Engineering Principles

FRAMEFORGE AI is designed around reliability, traceability, and human control.

**1. Deterministic Scene Segmentation**

Python identifies screenplay scene boundaries using scene headings. The AI analyses each scene without independently deciding scene numbering or ordering.

**2. AI Does Not Control the Database**

AI responses pass through a controlled processing pipeline:

`AI Response → JSON Parsing → Pydantic Validation → Python Verification → SQLite`

The AI does not directly modify database records or generate the final PDF.

**3. Character Verification**

- Characters not supported by the scene text are removed and flagged.
- Speakers identified from dialogue cues are added.
- V.O. and O.S. voices are distinguished from physically present characters.
- Merely mentioned characters are not automatically treated as present.

**4. Python-Based Calculations**

Appearance counts, first and last appearances, character roles, location grouping, scheduling, and call sheets are calculated using Python.

**5. Transparent Resource Classification**

Production resources are classified as:

- `EXPLICIT` – Directly mentioned in the screenplay.
- `INFERRED` – Derived from contextual screenplay information.
- `RECOMMENDED` – Suggested for production planning.

Generic equipment entries are filtered.

**6. Failure-Safe AI Processing**

- Failed chunks remain marked as `FAILED`.
- Error information is retained.
- Failed chunks can be retried independently.
- Successfully processed chunks are preserved.
- Missing information is flagged rather than fabricated.

**7. Human-Controlled Scheduling**

Schedules are generated deterministically and remain marked `PROPOSED` until approved.

The application does not invent shooting dates, availability, or contact details. Unknown information is marked `PENDING`.

---

## 📕 The Production Black Book

The Black Book is the central output of FRAMEFORGE AI.

It consolidates screenplay analysis and production planning information into a structured PDF document.

The generated document is designed to bring essential pre-production information together in one place.

It includes the sections configured by the application, with content such as:

- Screenplay and production overview.
- Scene breakdowns.
- Character registers.
- Location information.
- Production resources.
- Shooting schedules.
- Call sheets.
- Production planning details.

The PDF generation process uses structured database records rather than allowing AI-generated text to directly determine the final document.

## 🗄️ Database Design

FRAMEFORGE AI uses SQLite for persistent project management.

**Database location:**

```text
data/frameforge.db
```

### Main Database Tables

| Table | Purpose |
|---|---|
| projects | Production project information |
| documents | Uploaded screenplay documents |
| analyses | Analysis metadata |
| chunk_results | Individual AI chunk results |
| scenes | Extracted screenplay scenes |
| characters | Character information |
| scene_characters | Scene-character relationships |
| locations | Shooting location records |
| resources | Production resource records |
| shooting_days | Shooting day information |
| schedule_items | Scene-to-day assignments |
| call_sheets | Production call sheet data |
| progress | Scene completion tracking |
| stage_status | Pipeline stage tracking |

The database uses primary keys, foreign keys, cascading deletes, and indexes.

All SQL operations are centralised in:

```text
database/repository.py
```

**Important:** Running a complete new analysis replaces the existing scene records and resets the associated shooting schedule.

---

## 📂 Project Structure

```text
FRAMEFORGE-AI/
│
├── app.py
│
├── config/
│
├── core/
│   ├── loader
│   ├── preprocessor
│   ├── chunker
│   ├── extractor
│   ├── analyzers
│   ├── planner
│   ├── scheduler
│   ├── pipeline
│   └── black_book
│
├── ai/
│   ├── client
│   ├── prompts
│   ├── schemas
│   ├── parser
│   └── assistant
│
├── database/
│   └── repository.py
│
├── ui/
│
├── exports/
│   └── pdf_generator.py
│
├── tests/
│   └── data/
│
├── data/
│
├── generated/
│   └── blackbooks/
│
├── requirements.txt
├── .env.example
├── TESTING.md
└── README.md
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.12
- NVIDIA API key
- Internet connection for API access and dependency installation

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd FRAMEFORGE-AI
```

### 2. Create a Virtual Environment

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create your environment file:

**Windows:**

```bash
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Add your NVIDIA API key:

```env
NVIDIA_API_KEY=your_nvidia_api_key
NVIDIA_MODEL=nvidia/nemotron-3-nano-30b-a3b
```

Get your API key from:

https://build.nvidia.com

**Security:** Never commit your `.env` file or expose your API key publicly.

### 5. Launch the Application

```bash
streamlit run app.py
```

Open the local Streamlit URL displayed in your terminal.

**First-time setup:** Navigate to `Settings → Test Connection` to verify API authentication and model availability.

The model can be configured through `NVIDIA_MODEL` or overridden for the current session through Settings. The default model ID is configurable and must be verified with the connection test.

---

## 🎥 Application Demo (5-Minute Walkthrough)

Follow this workflow to explore the complete application.

| Step | Action | Expected Result |
|---|---|---|
| 01 | Create a New Production | Create a project and open Script Analysis. |
| 02 | Upload a screenplay | Upload `tests/data/sample_short.txt` containing 7 scenes. |
| 03 | Extract screenplay text | Preview the cleaned screenplay. |
| 04 | Run AI Analysis | Analyse scenes with chunk-level progress tracking. |
| 05 | Review Scene Breakdown | Edit, add, delete, and save scene information. |
| 06 | Manage Registers | Review characters, locations, and production resources. |
| 07 | Generate Shooting Schedule | Create a proposed schedule, move scenes, and approve it. |
| 08 | Generate Call Sheets | Enter confirmed call/wrap times and download PDFs. |
| 09 | Track Production | Mark scenes completed and retain progress across restarts. |
| 10 | Generate Black Book | Create and download the production Black Book PDF. |
| 11 | Use AI Production Assistant | Ask questions about the project. |

---

## 🧪 Testing & Verification

The project includes an automated test runner.

Run:

```bash
python -m tests.run_all
```

The latest recorded offline test results:

| Metric | Result |
|---|---:|
| Automated tests passed | 23 |
| Failed tests | 0 |
| Pass rate | 100% |

Additional verification included SQLite persistence checks, pipeline smoke tests with a stubbed Streamlit implementation, and visual inspection of generated PDF pages.

**Important:** These results represent offline testing. They do not establish successful live NVIDIA API integration or actual browser-level Streamlit behaviour.

For the complete test coverage, environment details, and pending verification checklist, see **[TESTING.md](TESTING.md)**.

---

## ⚠️ Known Limitations

- **Live NVIDIA integration:** Model availability, JSON compliance, rate limits, and `enable_thinking` behaviour require local verification.
- **OCR:** Image-only/scanned PDFs are not supported. Use text-based PDFs, DOCX, or TXT files.
- **Page estimation:** TXT/DOCX page numbers without explicit page breaks are estimated using approximately 55 lines per page.
- **Runtime estimation:** A one-page-per-minute rule of thumb is used.
- **Scene heading recognition:** Standard `INT.`, `EXT.`, `I/E`, and `SCENE n` formats are supported. Unusual formats are flagged for review.
- **Location matching:** Potential duplicates are suggested rather than automatically merged.
- **Extraction accuracy:** Real-world screenplay extraction accuracy has not yet been measured. No accuracy percentage is claimed.

---

## 🚀 Future Improvements

Potential development directions include:

- OCR support for scanned screenplay documents.
- Advanced screenplay format recognition.
- More comprehensive character and location relationship analysis.
- Improved production budgeting and cost estimation.
- Advanced scheduling with real-world availability integration.
- Collaborative production planning.
- More detailed production analytics and reporting.
- Benchmarking against manually annotated screenplays.

*These are potential enhancements, not claims about currently implemented functionality.*

---

## 👨‍💻 Development & Contribution

Contributions, bug reports, and feature suggestions are welcome.

If you discover an issue or have an idea to improve FRAMEFORGE AI, consider opening a GitHub Issue or submitting a Pull Request.

Please ensure that new functionality includes appropriate tests.

---

## 📜 License

Add your chosen open-source license before distributing the project. Until a license is included, standard copyright restrictions apply.

---

**FRAMEFORGE AI — From Script to Production. One Intelligent Black Book.** 🎬
