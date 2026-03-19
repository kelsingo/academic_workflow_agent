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