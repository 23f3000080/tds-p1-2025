# instructor/server.py
from flask import Flask, render_template, request, jsonify
from evaluate import check_mit_license, fetch_readme, llm_evaluate_text, playwright_check

app = Flask(__name__)

@app.route("/evaluate", methods=["POST"])
def evaluate():
    data = request.get_json(force=True)
    print("Received payload:", data)

    repo_url = data.get("repo_url", "")
    pages_url = data.get("pages_url", "")
    checks = data.get("checks", [])
    js_checks = data.get("js_checks", [])

    results = {}

    # Check MIT license
    if "Repo has MIT license" in checks:
        results["mit_license"] = check_mit_license(repo_url)

    # Evaluate README
    if "README.md is professional" in checks:
        readme = fetch_readme(repo_url) or ""
        results["readme_eval"] = llm_evaluate_text(readme)

    # Run Playwright JS checks if any
    if js_checks:
        results["js_checks"] = playwright_check(pages_url, js_checks)
    else:
        results["js_checks"] = []

    return jsonify({"status": "ok", "results": results})


if __name__ == "__main__":
    app.run(port=5001)
