import os
from backend.API_request import send_request, parse_json
from backend.check_eligibility import eligible_check

CHECK_PROMPT = """
You are an academic workflow assistant. Your job is to extract and validate course load request submissions.

Extract the following fields from the student message:
- course_ids (list of course IDs, max 5, all unique)
- reason
- plan

Validation rules:
- All fields are required
- course_ids must contain 5 courses
- all course_ids must be unique
- If reason is vague/missing, set to null
- If plan is vague/missing, set to null
- Return valid=false if reason or plan is null
- REASON = WHY the student needs the courses (motivation, goals, deadlines)
- PLAN = HOW the student will manage the workload (study methods, time management, support)

Return ONLY JSON:
{
  "valid": true,
  "missing_fields": [],
  "errors": [],
  "data": {
    "student_id": 25372,
    "course_ids": [],
    "reason": "",
    "plan": ""
  }
}

Rules:
- If a field is missing, put it in missing_fields
- If validation fails, put explanation in errors
- If validation fails, set valid=false
- If field missing, set value to null

Student Message:
{{student_prompt}}
""".strip()

def build_n_validate(api_key, user_input):
    prompt = CHECK_PROMPT.replace(
        "{{student_prompt}}",
        user_input
    )

    result = send_request(api_key, prompt)

    return result


# def validate_course_rules(extracted_data):
#     courses = extracted_data.get("course_ids")

#     if not courses:
#         return False, "No courses found."

#     # Normalize
#     courses = [c.upper().strip() for c in courses]

#     # Rule 1 — max 5
#     if len(courses) > 5:
#         return False, "Maximum 5 courses allowed."

#     # Rule 2 — unique
#     if len(courses) != len(set(courses)):
#         return False, "Duplicate courses detected."

#     return True, "Validation passed."

def main():
    api_key = os.environ.get("GEMINI_API_KEY")

    # user_input = input("Enter request: ")
    user_input = "I'd like to submit a maximum course load request for this semester. Courses: CS101, MATH201, ENG301, HIS101, SOCI202. My plan is to complete my CS major requirements by Year 3. Reason: I am ahead on electives and need to catch up on core units."

    validation = build_n_validate(api_key, user_input)

    print("Validation:", validation)

    if not validation.get("valid"):
        print("Validation failed")

        if validation.get("missing_fields"):
            print("Missing fields:")
            for field in validation["missing_fields"]:
                print("-", field)

        if validation.get("errors"):
            print("Errors:")
            for err in validation["errors"]:
                print("-", err)

        print("Please rewrite your request.")

        return

    # If no null values
    print(eligible_check(validation["data"]))


if __name__ == "__main__":
    main()