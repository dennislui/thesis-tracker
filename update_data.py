#!/usr/bin/env python3
"""
update_data.py — Push a new word count entry to the thesis tracker on GitHub.

Usage:
  python3 update_data.py <word_count> "<insight_text>"

Example:
  python3 update_data.py 6150 "Great progress — 6,150 words and climbing!"

This script reads github_credentials.json (never committed to GitHub),
fetches the current data.json from your GitHub repo via the API,
appends today's entry, and pushes the update as a new commit.
"""

import sys
import json
import base64
import urllib.request
import urllib.error
import datetime
import os


def main():
    # ── 1. Parse arguments ───────────────────────────────────────────────────
    if len(sys.argv) < 3:
        print("Usage: python3 update_data.py <word_count> \"<insight>\"")
        sys.exit(1)

    word_count = int(sys.argv[1])
    insight = sys.argv[2]
    today = datetime.date.today().isoformat()

    # ── 2. Load GitHub credentials ───────────────────────────────────────────
    # github_credentials.json lives in the same folder as this script.
    # It is listed in .gitignore and should NEVER be committed to your repo.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    creds_file = os.path.join(script_dir, "github_credentials.json")

    if not os.path.exists(creds_file):
        print(f"ERROR: Credentials file not found at {creds_file}")
        print("Please copy github_credentials.example.json → github_credentials.json")
        print("and fill in your GitHub username, repo name, and Personal Access Token.")
        sys.exit(1)

    with open(creds_file) as f:
        creds = json.load(f)

    token    = creds["github_token"]
    owner    = creds["github_username"]
    repo     = creds["github_repo"]
    api_url  = f"https://api.github.com/repos/{owner}/{repo}/contents/data.json"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "thesis-tracker-bot"
    }

    # ── 3. Fetch current data.json from GitHub ───────────────────────────────
    req = urllib.request.Request(api_url, headers=headers, method="GET")
    sha = None
    try:
        with urllib.request.urlopen(req) as resp:
            file_info = json.loads(resp.read().decode())
        sha = file_info["sha"]
        # GitHub returns content as base64 with potential newlines
        raw = base64.b64decode(file_info["content"].replace("\n", ""))
        current_data = json.loads(raw.decode())
        print(f"Fetched current data.json (SHA: {sha[:7]}...)")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("data.json not found in repo — creating fresh file.")
            current_data = {
                "target": 18000,
                "deadline": "2026-09-01",
                "docTitle": "Introduction",
                "docId": "1yDRVeYzLPLKFpODZJdvkjqppWw94ryV6otT7ae8tneY",
                "history": []
            }
        else:
            body = e.read().decode()
            print(f"GitHub API error {e.code}: {body}")
            sys.exit(1)

    # ── 4. Append today's entry (replace if already exists for today) ────────
    history = current_data.get("history", [])
    history = [entry for entry in history if entry["date"] != today]
    history.append({
        "date": today,
        "wordCount": word_count,
        "insight": insight
    })
    current_data["history"] = history
    print(f"Updated history: {len(history)} entries. Latest: {word_count} words on {today}.")

    # ── 5. Push updated data.json back to GitHub ─────────────────────────────
    new_content = json.dumps(current_data, indent=2, ensure_ascii=False)
    new_content_b64 = base64.b64encode(new_content.encode()).decode()

    payload = {
        "message": f"tracker: {word_count} words on {today}",
        "content": new_content_b64,
        "committer": {
            "name": "Thesis Tracker Bot",
            "email": "tracker@noreply.github.com"
        }
    }
    if sha:
        payload["sha"] = sha  # Required for updates (not creates)

    data = json.dumps(payload).encode()
    req = urllib.request.Request(api_url, data=data, headers=headers, method="PUT")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        commit_url = result["commit"]["html_url"]
        print(f"✓ Pushed successfully!")
        print(f"  Commit: {commit_url}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"GitHub push error {e.code}: {body}")
        sys.exit(1)


if __name__ == "__main__":
    main()
