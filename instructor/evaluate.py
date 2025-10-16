# instructor/evaluate.py
import os
import json
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def check_mit_license(repo_url):
    """Check if repo has a LICENSE file (MIT or otherwise)."""
    api_url = repo_url.replace("https://github.com/", "https://api.github.com/repos/")
    url = f"{api_url}/contents/LICENSE"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    r = requests.get(url, headers=headers)
    return r.status_code == 200

def fetch_readme(repo_url):
    """Fetch README.md from GitHub repository."""
    api_url = repo_url.replace("https://github.com/", "https://api.github.com/repos/")
    url = f"{api_url}/readme"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8")

def llm_evaluate_text(text, prompt_type="readme"):
    """Use OpenAI API to evaluate student text (like README quality)."""
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    system = "You are an evaluator of student submissions."
    user_prompt = (
        f"Evaluate the following {prompt_type} for clarity, correctness, and completeness. "
        "Return JSON: {\"score\": 0-10, \"notes\": \"...\"}.\n\n"
        f"Text:\n{text[:2000]}"
    )
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
    r.raise_for_status()
    result = r.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"score": 0, "notes": result}

def playwright_check(page_url, js_checks):
    """Run JS checks on student submission using Playwright."""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(page_url, timeout=30000)
        for check in js_checks:
            try:
                ok = page.evaluate(check)
                results.append({"check": check, "passed": bool(ok)})
            except Exception as e:
                results.append({"check": check, "passed": False, "error": str(e)})
        browser.close()
    return results
