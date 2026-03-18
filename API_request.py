import os 
import requests
import json 
import re 

required_fields = ['course_ids', 'reason', 'plan']
EXTRACT_MAX_COURSELOAD = """
You are 
Extract the following fields from the student message:

- course_ids (list of course IDs, max 5)
- reason
- plan

Return ONLY JSON. Do not generate or explain anything.

If a field is missing, return it as null.

Message:
{{student_prompt}}
""".strip()

state = {
    "course_ids": None,
    "reason": None,
    "plan": None
}
def parse_json(text_blob: str):
    text_blob = text_blob.strip()

    try:
        return json.loads(text_blob)
    except:
        pass

    pattern = r"```json(.*?)```"
    matches = re.findall(pattern, text_blob, re.DOTALL)

    for json_string in matches:
        try:
            return json.loads(json_string.strip())
        except:
            continue

    return {}

def build_prompt(input):
    prompt = EXTRACT_MAX_COURSELOAD.replace("{{student_prompt}}", input)
    return prompt 

def send_request(api_key, prompt):
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    data = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    response = requests.post(
        url,
        headers=headers,
        json=data,
    )
    print(response)
    result = response.json() 
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    data = parse_json(text)
    return data 

def update_state(state, extracted):
    for key in state: 
        if extracted.get(key):
            state[key] = extracted[key]   

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    print(api_key)
    user_input = "I need to request for maximum courseload to enroll in these 5 courses: CS101, CS103, CS208"
    prompt = build_prompt(user_input)
    output = send_request(api_key, prompt)
    print(output)
    update_state(state, output)

if __name__ == "__main__":
    main()


