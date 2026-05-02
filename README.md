# Academic Workflow Agent

This project implements a backend pipeline for an academic agent with an integrated LLM. It processes student requests for maximum courseload by extracting structured fields (`course_ids`, `reason`, `plan`) from natural language input using the Gemini API.

The pipeline then evaluates eligibility using student and course information datasets. Based on the results, the system proceeds to request advisor approval when necessary and ultimately notifies the school system for final processing.

---

## Code Usage

### 1. Set up API Key

Set your Gemini API key as an environment variable:

```bash
export GEMINI_API_KEY="your_api_key_here"
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
```bash
sqlite3 fuv_data.db
.tables 
```

View script to create SQL database: ``` script.sql ``` 

### Logic Handler
Function ```check_eligibility.py``` load data from ```fuv_data.db``` and check students' elegibility for enrolling in 5 courses upon receiving request. 

1. Eligibility criteria: 

- Check whether requested courses are available in the current semester. 
- Check whether request is sent before the deadline.
- Check whether student has enough credits for the 5 requested courses. 

2. Load data: request deadline, course credits, student data. 


