import os
import re
import json
from backend.API_request import build_prompt, send_request, update_state, parse_json, required_fields
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

state = {
    "course_ids": None,
    "reason": None,
    "plan": None
}

def parse_prompts_from_file(filepath: str) -> List[Dict]:
    """Extract labeled prompts from the .txt file."""
    prompts = []
    with open(filepath, "r") as f:
        content = f.read()

    # Match blocks like [P01] (Title)? \n"...prompt text..."
    pattern = r'\[(P\d+)\](?: (.+?))?\s*\n"(.+?)"'
    matches = re.findall(pattern, content, re.DOTALL)

    for pid, title, text in matches:
        prompts.append({
            "id": pid,
            "title": (title or "").strip(),
            "text": text.strip()
        })

    return prompts

def run_tests(filepath: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    prompts = parse_prompts_from_file(filepath)

    print(f"Found {len(prompts)} prompts. Running...\n")
    print("=" * 60)

    for p in prompts:
        print(f"[{p['id']}] {p['title']}")
        print(f"Input: {p['text'][:80]}...")

        prompt = build_prompt(p['text'])
        raw_output = send_request(api_key, prompt)

        if isinstance(raw_output, dict):
            parsed = raw_output
        else:
            parsed = parse_json(raw_output)

        if not isinstance(parsed, dict):
            print("⚠️ Invalid parsed output:", parsed)
            parsed = {}

        missing = [f for f in required_fields if not parsed.get(f)]

        print(f"Output: {json.dumps(parsed, indent=2)}")
        print(f"Missing fields: {missing if missing else 'None'}")
        print("-" * 60)

if __name__ == "__main__":
    file = input("Name of test file that you want to run: ")
    file_path = os.path.join(BASE_DIR, file)
    run_tests(file_path)