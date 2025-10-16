from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import sys
import uuid
import tempfile
import shutil
import traceback
from flask_cors import CORS
import subprocess  # <-- Added to run server.py automatically

from .github_utils import create_repo, create_file, add_license, enable_github_pages, wait_for_pages_ok
from .utils import verify_secret, post_evaluation
from .llm_generator import call_llm_generate
from .attachments import save_data_uri

load_dotenv()

app = Flask(__name__)
CORS(app)

# Load environment variables
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['EMAIL'] = os.getenv("EMAIL")
app.config['GITHUB_TOKEN'] = os.getenv("GITHUB_TOKEN")


# --- START server.py automatically ---
server_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "instructor", "server.py")
)
server_process = subprocess.Popen([sys.executable, server_path])
print(f"Started server.py with PID: {server_process.pid}")
# --- END server.py automatically ---


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

        # Response placeholder
        resp = {"status": "accepted", "message": "Processing your request."}

        # Create temporary directory for attachments
        tmpdir = tempfile.mkdtemp(prefix="task_")
        saved = []

        try:
            # Process attachments
            for att in attachments:
                name = att.get("name")
                url = att.get("url")
                if url and url.startswith("data:"):
                    fname = save_data_uri(url, tmpdir)
                    saved.append({"name": name, "path": fname})

            # Generate files via LLM
            files = call_llm_generate(brief, saved)

        finally:
            # Clean up temporary files
            shutil.rmtree(tmpdir)

        # Create GitHub repo
        repo_name = make_repo_name(task, email)
        repo_meta = create_repo(repo_name, private=False, description=f"Auto-generated for {task}")
        owner = repo_meta['owner']['login']
        repo_full_name = repo_meta['full_name']

        # Push files to repo
        prepare_and_push_repo(repo_full_name, files, owner=owner)

        # Enable GitHub Pages
        enable_github_pages(repo_full_name, branch="main", folder="/")
        pages_url = f"https://{owner}.github.io/{repo_name}/"
        ok = wait_for_pages_ok(pages_url, timeout=300)

        # Get latest commit SHA
        import requests
        commits_url = f"https://api.github.com/repos/{repo_full_name}/commits"
        r = requests.get(
            commits_url,
            headers={"Authorization": f"token {os.environ.get('GITHUB_TOKEN')}"}
        )
        r.raise_for_status()
        commit_sha = r.json()[0]["sha"]

        # Send evaluation payload
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

        # Return final response
        resp.update({
            "repo_url": payload["repo_url"],
            "pages_url": pages_url,
            "commit_sha": commit_sha
        })

        return jsonify(resp), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
