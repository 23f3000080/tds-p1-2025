# server/app.py
import os
import uuid
import tempfile
import shutil
import traceback
import time
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

from .github_utils import create_repo, create_file, add_license, enable_github_pages, wait_for_pages_ok
from .llm_generator import call_llm_generate
from .attachments import save_data_uri
from instructor.evaluate import check_mit_license, fetch_readme, llm_evaluate_text, playwright_check

load_dotenv()

app = Flask(__name__)
CORS(app)

# Load environment variables
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['EMAIL'] = os.getenv("EMAIL")
app.config['GITHUB_TOKEN'] = os.getenv("GITHUB_TOKEN")


# ------------------- UTILS MERGED -------------------
def verify_secret(provided_secret: str):
    secret = os.getenv("SECRET_KEY")
    if not secret:
        return "SECRET_KEY not set in environment", 500
    return provided_secret == secret


def post_evaluation(evaluation_url: str, payload: dict, max_retries: int=6):
    """
    POST to evaluation_url. On failure, retry with exponential backoff (1,2,4,8...).
    Returns response code or raises.
    """
    headers = {"Content-Type": "application/json"}
    delay = 1
    for attempt in range(max_retries):
        try:
            r = requests.post(evaluation_url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                return r
            # else retry
        except Exception:
            pass
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"Failed to POST evaluation after {max_retries} attempts")


# ------------------- ROUTES -------------------
@app.route("/")
def home():
    return render_template("index.html")


# Generate unique repo name
def make_repo_name(task: str, email: str):
    task = task.replace(" ", "-").lower()
    return f"{task}-{uuid.uuid4().hex[:6]}"


# Push generated files to GitHub repo
def prepare_and_push_repo(repo_full_name: str, files: list, owner: str):
    for file in files:
        file_path = file['path']
        file_content = file['content']
        create_file(repo_full_name, file_path, file_content, f"Add {file_path}")
    add_license(repo_full_name, owner=owner)


@app.route("/api-endpoint", methods=["POST"])
def api_endpoint():
    try:
        body = request.get_json(force=True)

        email = body.get("email")
        secret = body.get("secret")
        task = body.get("task")
        round_num = body.get("round")
        nonce = body.get("nonce")
        brief = body.get("brief", "")
        checks = body.get("checks", [])
        attachments = body.get("attachments", [])
        evaluation_url = body.get("evaluation_url")

        # Verify secret key
        if not verify_secret(secret):
            return jsonify({"error": "Secret mismatch"}), 400

        resp = {"status": "accepted", "message": "Processing your request."}

        tmpdir = tempfile.mkdtemp(prefix="task_")
        saved = []

        try:
            for att in attachments:
                name = att.get("name")
                url = att.get("url")
                if url and url.startswith("data:"):
                    fname = save_data_uri(url, tmpdir)
                    saved.append({"name": name, "path": fname})

            files = call_llm_generate(brief, saved)
        finally:
            shutil.rmtree(tmpdir)

        repo_name = make_repo_name(task, email)
        repo_meta = create_repo(repo_name, private=False, description=f"Auto-generated for {task}")
        owner = repo_meta['owner']['login']
        repo_full_name = repo_meta['full_name']

        prepare_and_push_repo(repo_full_name, files, owner)

        enable_github_pages(repo_full_name, branch="main", folder="/")
        pages_url = f"https://{owner}.github.io/{repo_name}/"
        wait_for_pages_ok(pages_url, timeout=600)  # increase to 10 mins

        commits_url = f"https://api.github.com/repos/{repo_full_name}/commits"
        r = requests.get(
            commits_url,
            headers={"Authorization": f"token {os.environ.get('GITHUB_TOKEN')}"}
        )
        r.raise_for_status()
        commit_sha = r.json()[0]["sha"]

        payload = {
            "email": email,
            "task": task,
            "round": round_num,
            "nonce": nonce,
            "repo_url": f"https://github.com/{repo_full_name}",
            "commit_sha": commit_sha,
            "pages_url": pages_url
        }
        post_evaluation(evaluation_url, payload)

        resp.update({
            "repo_url": payload["repo_url"],
            "pages_url": pages_url,
            "commit_sha": commit_sha
        })

        return jsonify(resp), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/evaluate", methods=["POST"])
def evaluate():
    data = request.get_json(force=True)
    print("Received payload:", data)

    repo_url = data.get("repo_url", "")
    pages_url = data.get("pages_url", "")
    checks = data.get("checks", [])
    js_checks = data.get("js_checks", [])

    results = {}

    if "Repo has MIT license" in checks:
        results["mit_license"] = check_mit_license(repo_url)

    if "README.md is professional" in checks:
        readme = fetch_readme(repo_url) or ""
        results["readme_eval"] = llm_evaluate_text(readme)

    if js_checks:
        results["js_checks"] = playwright_check(pages_url, js_checks)
    else:
        results["js_checks"] = []

    return jsonify({"status": "ok", "results": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
