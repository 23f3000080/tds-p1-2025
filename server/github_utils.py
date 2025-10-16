# server/github_utils.py
import os

import requests, time

from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_URL = "https://api.github.com"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# create repo
def create_repo(repo_name: str, private: bool=False, description: str=""):
    url = f"{GITHUB_API_URL}/user/repos"
    payload = {
        "name": repo_name,
        "private": private,
        "description": description,
        "auto_init": False,
    }
    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()

# create file in repo
def create_file(repo_full_name: str, file_path: str, content: str, commit_message: str, branch: str="main"):
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/contents/{file_path}"
    data = {
        "message": commit_message,
        "content": content.encode("utf-8").decode("utf-8"),
        "branch": branch
    }

    import base64
    data["content"] = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    resp = requests.put(url, json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def add_license(repo_full_name: str, owner: str=""):
    """Add MIT LICENSE file (simple template)."""
    mit = """MIT License

Copyright (c) {year} {owner}

Permission is hereby granted... (standard MIT)
"""
    content = mit.format(year=time.gmtime().tm_year, owner=owner or repo_full_name.split("/")[0])
    return create_file(repo_full_name, "LICENSE", content, "Add MIT license")


def enable_github_pages(repo_full_name: str, branch: str="main", folder: str="/"):
    """Enable GitHub Pages via REST API. Returns pages status or raises."""
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/pages"
    payload = {"source": {"branch": branch, "path": folder}}
    resp = requests.post(url, json=payload, headers={**HEADERS, "Accept": "application/vnd.github.switcheroo-preview+json"})
    # If already enabled, API may return 201/202 or 422; handle accordingly.
    if resp.status_code not in (201, 202, 204):
        # If already exists, try GET
        if resp.status_code == 422:
            # try GET
            getresp = requests.get(url, headers=HEADERS)
            getresp.raise_for_status()
            return getresp.json()
        resp.raise_for_status()
    return resp.json()


def wait_for_pages_ok(pages_url: str, timeout: int=120):
    """Poll pages_url until a 200 OK or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(pages_url, timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False