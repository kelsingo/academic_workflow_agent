# Academic Workflow Agent

This project implements a backend pipeline for an academic agent with an integrated LLM. It processes student requests for maximum courseload by extracting structured fields (`course_ids`, `reason`, `plan`) from natural language input using the Gemini API.

The pipeline then evaluates eligibility using student and course information datasets. Based on the results, the system proceeds to request advisor approval when necessary and ultimately notifies the school system for final processing.

## Project Structure
```
academic_workflow_agent/
├── backend/
│   ├── main.py               
│   ├── validate_info.py      - LLM extract + field validation
│   ├── check_eligibility.py  - Check DB eligibility 
│   ├── data_adapter.py       - DB helpers (load/save)
│   ├── send_mail.py          - Send Gmail
│   ├── classify_llm.py       - Classify reply & Suggest fix
│   └── check_mail.py         - Check inbox automatically
├── datasets/
│   └── fuv_data.db
└── frontend/
    └── web.html
```

## Start Program

Terminal 1 — API server:
```bash
cd academic_workflow_agent
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 — Gmail inbox:
```bash
cd academic_workflow_agent
python -m backend.check_mail
```

Browser — open with Live Server:
```bash
open frontend/web.html
```

---

## Code Usage

### 1. Set up environment
```bash
cp .env.example .env
```

#### Set up API Key

Set your Gemini API key as an environment variable:

For MacOS and Linux:
```bash
export GEMINI_API_KEY="your_api_key_here"
```
For Windows' PowerShell:
```bash
$env:GEMINI_API_KEY="your__api_key_here"
```


## Backend 
### Datasets
Database is stored using SQLite3. To view database:

**View all tables:**
```bash
sqlite3 datasets/fuv_data.db ".tables"
```

**Query specific tables:**
```bash
sqlite3 datasets/fuv_data.db

# View students table
SELECT * FROM students LIMIT 5;

# View course requests
SELECT * FROM course_load_requests;

# View advisors
SELECT * FROM advisors;

# View courses available this semester
SELECT * FROM course_2526 LIMIT 10;

# View registration deadlines
SELECT * FROM maxcourse_deadline;

# Exit sqlite3
.quit
```

**Or query directly from terminal:**
```bash
sqlite3 datasets/fuv_data.db "SELECT * FROM students LIMIT 5;"
sqlite3 datasets/fuv_data.db "SELECT * FROM course_load_requests;"
```
**Add new table to fuv_data.db:**
```bash
python3 sql_create.py --table-name "table name" --csv-file "csv file contains your table" --table-schema "SQL statements to create your table" 
```

### Logic Handler
Function ```check_eligibility.py``` load data from ```fuv_data.db``` and check students' elegibility for enrolling in 5 courses upon receiving request. 

1. Eligibility criteria: 

- Check whether requested courses are available in the current semester. 
- Check whether request is sent before the deadline.
- Check whether student has enough credits for the 5 requested courses. 

2. Load data: request deadline, course credits, student data. 
