#!/usr/bin/env python3
"""
Evaluate multiple repositories with a local Ollama model (e.g., deepseek-r1:8b).

Usage:
  1) Make sure Ollama is running locally (the background service starts when you open the app).
  2) Ensure the model is available: `ollama pull deepseek-r1:8b`
  3) Put your repositories under a parent folder, e.g., ./cloned_repo/{username}/{repo}
  4) Run this script:
       python3 evaluate_repos_with_ollama.py --root ./cloned_repo --model deepseek-r1:8b
  5) Reports will be saved under ./reports/{repo_name}.md

Notes:
- Uses the Ollama Chat API: http://localhost:11434/api/chat
- Keeps inputs within reasonable size limits by sampling representative files.
"""

import os
import re
import sys
import json
import argparse
import pathlib
import requests
from datetime import datetime

FILE_EXTS = {
    ".py",".js",".ts",".tsx",".jsx",".java",".go",".rb",".rs",".cpp",".c",".cc",".h",".hpp",".cs",".php",
    ".swift",".kt",".m",".mm",".scala",".pl",".r",".jl",".lua",".sh",".bat",".ps1",".fish",".sql",
    ".md",".rst",".txt",".yaml",".yml",".toml",".ini",".cfg",".env",".json",".xml",".gradle",".sbt",".make",".mk"
}

PREFERRED_FILES = [
    "README.md", "README", "readme.md", "readme",
    "CONTRIBUTING.md", "LICENSE", "LICENSE.md",
    "requirements.txt","pyproject.toml","setup.py","Pipfile","Pipfile.lock",
    "package.json","package-lock.json","pnpm-lock.yaml","yarn.lock",
    "go.mod","go.sum","Cargo.toml","Cargo.lock",
    "pom.xml","build.gradle","settings.gradle","gradle.properties",
    "composer.json","Gemfile","Gemfile.lock",
    ".env.example",".env.sample"
]

MAX_FILES_PER_REPO = 24         # cap the number of files we feed the model
MAX_CHARS_PER_FILE = 20000      # cap per file to avoid overloading context
TRUNC_HEAD_TAIL = 5000          # when truncating, keep this many chars from head and tail

SYSTEM_PROMPT = """You are a senior software reviewer and code auditor.
Produce a clear, actionable evaluation for each repository you are given.
Focus on: purpose, architecture, key files, correctness, security, performance, code quality, tests, docs, and quick-start steps.
Point out severe issues first and propose fixes or code snippets.
Return a concise but thorough markdown report, including a table of prioritized recommendations.
"""

REPO_EVAL_INSTRUCTIONS = """You will receive a repository snapshot with:
1) A tree of files (shortened).
2) Selected file contents (truncated where necessary).

Please write a report with the following sections:
- Project Summary
- How to Run / Quickstart
- Architecture & Key Components
- Code Quality & Maintainability (style, structure, readability)
- Correctness & Reliability (edge cases, bugs, error handling)
- Security Considerations (input validation, secrets, deps)
- Performance Considerations (hot paths, complexity, I/O)
- Dependencies & Supply Chain (pinning, vulnerabilities to check)
- Testing (coverage, missing tests, suggested cases)
- Documentation (what’s good, what to add)
- Prioritized Recommendations (table with: Priority | Area | Recommendation | Rationale)
End with a short checklist of next steps.
"""

def is_textlike(path: pathlib.Path) -> bool:
    if path.suffix.lower() in FILE_EXTS:
        return True
    # crude binary sniff
    try:
        with open(path, 'rb') as f:
            chunk = f.read(1024)
        if b'\x00' in chunk:
            return False
        return True
    except Exception:
        return False

def safe_read(path: pathlib.Path) -> str:
    try:
        data = path.read_text(errors="replace")
    except Exception as e:
        return f"<<ERROR READING FILE {path.name}: {e}>>"
    if len(data) <= MAX_CHARS_PER_FILE:
        return data
    head = data[:TRUNC_HEAD_TAIL]
    tail = data[-TRUNC_HEAD_TAIL:]
    omitted = len(data) - (len(head) + len(tail))
    return f"<<TRUNCATED ({omitted} chars omitted)>>\n" + head + "\n...\n" + tail

def shortlist_files(repo_root: pathlib.Path):
    # Prefer key project files, then add code files until we reach MAX_FILES_PER_REPO
    selected = []
    # 1) add preferred files if present
    for name in PREFERRED_FILES:
        p = repo_root / name
        if p.exists() and p.is_file():
            selected.append(p)

    # 2) scan for code/text files
    others = []
    for path in repo_root.rglob("*"):
        if path.is_file() and path.suffix and is_textlike(path):
            # skip files already selected
            if path in selected:
                continue
            # skip minified bundles and huge lockfiles by simple heuristics
            if path.name.endswith(".min.js") or path.name.endswith(".map"):
                continue
            if path.name in ("pnpm-lock.yaml","yarn.lock","package-lock.json","Cargo.lock","go.sum") and path.stat().st_size > 3_000_000:
                continue
            others.append(path)

    # prioritize small-to-medium files to fit more diverse context
    others.sort(key=lambda p: (p.stat().st_size, p.name))

    # fill up remaining slots
    for p in others:
        if len(selected) >= MAX_FILES_PER_REPO:
            break
        selected.append(p)

    return selected

def make_tree(repo_root: pathlib.Path, max_entries=400):
    # Produce a lightweight tree listing (up to max_entries lines)
    lines = []
    for path in repo_root.rglob("*"):
        rel = path.relative_to(repo_root)
        if len(lines) >= max_entries:
            lines.append("... (truncated)")
            break
        if path.is_dir():
            lines.append(f"{rel}/")
        else:
            lines.append(str(rel))
    return "\n".join(lines)

def chat_ollama(model: str, messages: list, temperature: float = 0.2, base_url: str = "http://localhost:11434"):
    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    resp = requests.post(url, json=payload, timeout=600)
    resp.raise_for_status()
    data = resp.json()
    # standardize across ollama versions: message content may be in "message"
    if "message" in data and isinstance(data["message"], dict):
        return data["message"].get("content", "")
    # or conversation can have "messages"
    if "messages" in data and data["messages"]:
        return data["messages"][-1].get("content", "")
    # fallback
    return data.get("content", "")

def evaluate_repo(model: str, repo_root: pathlib.Path, out_dir: pathlib.Path):
    repo_name = repo_root.name
    tree = make_tree(repo_root)

    files = shortlist_files(repo_root)
    parts = [f"# Repository: {repo_name}", "", "## File Tree (short)",
             "```", tree, "```", "", "## Selected Files"]
    for p in files:
        rel = p.relative_to(repo_root)
        parts.append(f"\n### {rel}\n")
        content = safe_read(p)
        # fence based on extension for nicer formatting
        ext = p.suffix.lower().lstrip(".") or "txt"
        parts.append(f"```{ext}\n{content}\n```")

    user_blob = "\n".join(parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": REPO_EVAL_INSTRUCTIONS + "\n\n" + user_blob}
    ]

    print(f"[+] Evaluating {repo_name} with model {model} ...")
    try:
        result = chat_ollama(model=model, messages=messages)
    except requests.exceptions.RequestException as e:
        result = f"ERROR contacting Ollama for {repo_name}: {e}\nIs Ollama running and is the model pulled?"

    out_path = out_dir / f"{repo_name}.md"
    out_path.write_text(result)
    print(f"[✓] Wrote report: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Evaluate repos using a local Ollama model")
    parser.add_argument("--root", type=str, required=True, help="Root folder containing repos (e.g., ./cloned_repo)")
    parser.add_argument("--model", type=str, default="deepseek-r1:8b", help="Ollama model name (default: deepseek-r1:8b)")
    parser.add_argument("--out", type=str, default="./reports", help="Output folder for reports")
    args = parser.parse_args()

    root = pathlib.Path(args.root).expanduser().resolve()
    out_dir = pathlib.Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not root.exists():
        print(f"ERROR: root path not found: {root}")
        sys.exit(1)

    # If the structure contains usernames/{repo}, allow evaluating each leaf repo
    # We treat any directory that contains code files as a "repo"
    candidates = []
    for p in root.iterdir():
        if p.is_dir():
            # If p has nested dirs that look like repos, include both levels
            subdirs = [d for d in p.iterdir() if d.is_dir()]
            if subdirs:
                for d in subdirs:
                    candidates.append(d)
            else:
                candidates.append(p)

    # Filter to those that have at least one textlike code file
    repos = []
    for c in candidates:
        has_code = False
        for path in c.rglob("*"):
            if path.is_file() and is_textlike(path):
                has_code = True
                break
        if has_code:
            repos.append(c)

    if not repos:
        print("No repositories with code-like files were found under", root)
        sys.exit(0)

    print(f"Found {len(repos)} repo(s) to evaluate.\n")
    for repo in repos:
        evaluate_repo(args.model, repo, out_dir)

if __name__ == "__main__":
    main()
