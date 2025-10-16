# server/llm_generator.py
import os
import json
import base64
import requests
from urllib.parse import unquote

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def decode_data_url(data_url: str):
    """
    Decode data URLs of the form data:<mime>;base64,<data> or data:<mime>,<data>.
    Returns decoded text (UTF-8) or binary notice if not text.
    """
    if not data_url.startswith("data:"):
        return None

    try:
        header, encoded = data_url.split(",", 1)
        is_base64 = ";base64" in header
        if is_base64:
            decoded_bytes = base64.b64decode(encoded)
        else:
            decoded_bytes = unquote(encoded).encode("utf-8")

        # Try UTF-8 decode (if text file)
        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return "<binary file content not shown>"

    except Exception as e:
        return f"<error decoding data url: {str(e)}>"


def summarize_file_content(content: str, max_chars: int = 500):
    """
    Summarize file content for prompt inclusion.
    For long files, only include first few lines.
    """
    lines = content.strip().splitlines()
    sample = "\n".join(lines[:10])
    if len(content) > max_chars:
        return sample + f"\n... (file truncated, {len(content)} characters total)"
    return content


def build_prompt_for_brief(brief: str, attachments: list):
    """
    Build a contextual LLM prompt using decoded attachment content.
    Each attachment can be text, markdown, CSV, JSON, etc.
    """
    system = (
        "You are a web app generator. Given a brief and attached files, "
        "generate a minimal, static, single-page web app (HTML/CSS/JS) "
        "that fulfills the brief. Always output valid JSON in the format: "
        '{"files":[{"path":"index.html","content":"..."},{"path":"README.md","content":"..."}]}'
    )

    file_summaries = []
    for att in attachments:
        name = att.get("name", "attachment")
        url = att.get("url")
        if not url:
            continue

        content = decode_data_url(url)
        if content:
            summary = summarize_file_content(content)
            file_summaries.append(f"File: {name}\n{summary}")
        else:
            file_summaries.append(f"File: {name} (unreadable or invalid data URL)")

    if not file_summaries:
        file_summaries.append("No attachments provided.")

    user = (
        f"Task Brief:\n{brief}\n\n"
        f"Attached Files Summary:\n{chr(10).join(file_summaries)}\n\n"
        "Your output must:\n"
        "- Include a modern, responsive design (HTML/CSS, Bootstrap optional)\n"
        "- Show computed or visual results in index.html based on input files\n"
        "- Include a README.md explaining what the app does\n"
        "- Return only JSON, no extra commentary"
    )

    return system, user


def call_llm_generate(brief: str, attachments: list, model: str = "gpt-4o-mini"):
    """
    Call the OpenAI model to generate app files based on the brief + attachments.
    Always ensures index.html and README.md exist.
    """
    system, user = build_prompt_for_brief(brief, attachments)

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
    }

    resp = requests.post(OPENAI_URL, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]

    # Parse response JSON safely
    try:
        data = json.loads(text)
        files = data.get("files", [])
    except json.JSONDecodeError:
        files = [{"path": "index.html", "content": f"<pre>{text}</pre>"}]

    # Ensure README.md exists
    if not any(f["path"].lower() == "readme.md" for f in files):
        files.append({
            "path": "README.md",
            "content": "README: This app was generated automatically. Open index.html in your browser."
        })

    # Ensure index.html exists
    if not any(f["path"].lower() == "index.html" for f in files):
        files.append({
            "path": "index.html",
            "content": "<!DOCTYPE html><html><body><h1>Generated Output</h1></body></html>"
        })

    return files