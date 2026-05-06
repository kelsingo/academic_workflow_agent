# Academic Workflow Agent

This project implements a backend pipeline for an academic agent with an integrated LLM. It processes student requests for maximum courseload by extracting structured fields (`course_ids`, `reason`, `plan`) from natural language input using the Gemini API.

The pipeline then evaluates eligibility using student and course information datasets. Based on the results, the system proceeds to request advisor approval when necessary and ultimately notifies the school system for final processing.

---

## Code Usage

### 1. Set up API Key

Set your Gemini API key as an environment variable:

For MacOS and Linux:
```bash
export GEMINI_API_KEY="your_api_key_here"
```
For Windows' PowerShell:
```bash
$env:GEMINI_API_KEY="your__api_key_here"
```

### 2. Run extraction test 
```bash
python API_request.py
```

## Example Output 
```
{
  "course_ids": ["CS101", "CS103", "CS208"],
  "reason": null,
  "plan": null
}
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

---

## Start Program

```bash
# Terminal 1: Start backend
python3 backend/main.py

# Terminal 2: Start UI
open frontend/web.html
```


## Configuration

1. **Gmail Setup**
   ```bash
   cp .env.example .env
   # Edit .env with:
   # - Gmail: 
   # - App Password: 
   # - Gemini Key:
   ```