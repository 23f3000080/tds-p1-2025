# Instructor Task Sender

A web application for instructors to send coding/design tasks to students, including file attachments, automatic GitHub repository creation, and evaluation via an LLM-powered system.

---

## Features

- **Task Submission Form**: Submit tasks with student email, secret key, task brief, and optional attachments.
- **Attachment Support**: Upload multiple files in formats like `.txt`, `.csv`, `.md`, `.png`, etc.
- **Automatic GitHub Repo Creation**: Generates a repository for each task and pushes the generated app files.
- **License and README**: Adds MIT license automatically and ensures a professional README.md exists.
- **Live GitHub Pages Preview**: Enables GitHub Pages for easy preview of generated apps.
- **Evaluation System**: Evaluates submissions based on checks like license presence, README quality, and JS code correctness.
- **LLM Integration**: Uses OpenAI GPT models to generate files based on task briefs and attachments.

---

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, Bootstrap 5, JavaScript
- **Database**: No persistent DB required (uses GitHub repos for storage)
- **APIs & Libraries**:
  - GitHub REST API (repo creation, file upload, GitHub Pages)
  - OpenAI GPT API (automatic code/file generation)
  - Playwright (JavaScript checks on generated apps)
  - Python modules: `requests`, `dotenv`, `flask-cors`, `tempfile`, `shutil`

---

## Installation

1. Clone the repository:

```bash
git clone <repo-url>
cd <repo-folder>


pip install -r requirements.txt

SECRET_KEY=your_secret_key
EMAIL=your_email@example.com
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key

python app.py inside server folder
