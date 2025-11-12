#!/usr/bin/env python3
import os
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
import ollama

# ---------------- CONFIG ----------------
ROOT = Path(os.environ.get("REPOS_ROOT", str(Path(__file__).resolve().parent / "cloned_repos")))
OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs_json"
MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b")

IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'dist', 'build', '.idea', '.next',
    'out', 'target', 'vendor', 'venv', '.venv', '.DS_Store'
}

CODE_EXT = {
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.java', '.cpp', '.c', '.go', '.rs',
    '.html', '.css', '.json', '.php', '.rb', '.kt'
}

# ✅ Keep your original evaluation prompt exactly
from textwrap import dedent
PROMPT_TEMPLATE = dedent("""
You are grading ONE second-year CSE student project.
Analyze ONLY the code and README given below. Do NOT assume absent features.

GOALS
- Return a single, strictly valid JSON object (no markdown fences, no prose).
- Grade exactly 10 metrics, each an integer 0–10, then compute total_score (0–100).
- Every score MUST be justified with short, code-grounded evidence.
- If evidence is missing, score = 0 and say "evidence: not found".
- Evaluate ONE project only. Ignore references to other repos.
- Aim to finish in ONE attempt; if truly impossible due to insufficient evidence, set "needs_second_attempt": true (else false).

PROJECT CODE (trimmed excerpts):
{project_info}

RUBRIC (0–10 each, integers only)
1) feature_completion: features present vs expected for this domain; avoid guessing.
2) functionality: runs in principle; obvious bugs, missing wiring, broken flows.
3) ui_ux_interactivity: usability, responsiveness, event handling, state logic.
4) code_quality: readability, naming, modularity, dead code, duplication.
5) error_handling: input validation, edge cases, try/except, guards, fallbacks.
6) best_practices: folder structure, config/env separation, lint/test hints.
7) tech_stack_depth: beyond basics (frameworks, libs, APIs, build tooling).
8) github_usage: README, commits, branches/PRs, .gitignore, repo hygiene.
9) uniqueness_innovation: originality vs template/clone/tutorial.
10) ai_generated_score: 10 = very unlikely AI; 0 = highly AI-like patterns.

SCORING RULES
- All metric values must be integers 0–10. No floats.
- "ai_generated_score" is a score (10=human-like). Also include a label field "ai_generated_label": "Unlikely|Possibly|Likely".
- total_score = sum of all 10 metrics (0–100).
- Be conservative: no evidence → 0, partial → 3–6, strong → 7–9, exceptional → 10.

OUTPUT JSON SCHEMA (must match exactly these keys)
{
  "tech_stack": "string, main technologies observed",
  "feature_completion": 0-10,
  "functionality": 0-10,
  "ui_ux_interactivity": 0-10,
  "code_quality": 0-10,
  "error_handling": 0-10,
  "best_practices": 0-10,
  "tech_stack_depth": 0-10,
  "github_usage": 0-10,
  "uniqueness_innovation": 0-10,
  "ai_generated_score": 0-10,
  "ai_generated_label": "Unlikely|Possibly|Likely",
  "total_score": 0-100,
  "score_explanation": "single line: 10 semicolon-separated justifications in order of the metrics; each justification MUST cite filename or folder",
  "summary": "one concise sentence on impact/level",
  "strengths": "comma-separated concrete strengths tied to files",
  "improvements": "comma-separated concrete next steps tied to files",
  "needs_second_attempt": true|false
}

STRICTNESS & ANTI-HALLUCINATION
- Cite evidence with filenames/paths you actually saw.
- If you cannot find evidence for a metric, set it to 0 and explain: 'evidence: not found'.
- Do not invent libraries, tests, endpoints, or UI components.
- Output ONLY the JSON object. No backticks. No extra text.
""")

# ---------------- HELPERS ----------------
def get_last_commit(repo: Path):
    try:
        cmd = ["git", "-C", str(repo), "log", "-1", "--format=%cd"]
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip() or "Unknown"
    except Exception:
        return "Unknown"

def collect_project_info(repo: Path) -> str:
    chunks = []
    readme = repo / "README.md"
    if readme.exists():
        chunks.append("README.md:\n" + readme.read_text(errors="ignore")[:8000])

    code_files = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in CODE_EXT:
                try:
                    if p.stat().st_size < 200000:
                        code_files.append(p)
                except Exception:
                    pass

    code_files.sort(key=lambda f: f.stat().st_size if f.exists() else 0, reverse=True)
    total_chars = 0
    for f in code_files[:40]:
        try:
            text = f.read_text(errors="ignore")[:10000]
            chunks.append(f"\nFILE: {f.relative_to(repo)}\n{text}")
            total_chars += len(text)
            if total_chars > 60000:
                break
        except Exception:
            continue

    return "\n\n".join(chunks)[:60000]

def clean_json_output(output: str) -> str:
    # Remove markdown and escape junk
    cleaned = re.sub(r"```(?:json)?", "", output, flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned)
    cleaned = cleaned.replace("\\n", " ").replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned

def extract_json(output: str) -> dict:
    cleaned = clean_json_output(output)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1:
        candidate = cleaned[start:end+1]
        try:
            return json.loads(candidate)
        except Exception:
            fixed = re.sub(r",\s*}", "}", candidate)
            fixed = re.sub(r",\s*]", "]", fixed)
            return json.loads(fixed)
    raise ValueError("No valid JSON object found in model output")

# ---------------- CORE EVALUATION ----------------
def evaluate_repo(repo: Path) -> dict:
    info = collect_project_info(repo)
    prompt = PROMPT_TEMPLATE.replace("{project_info}", info)

    print(f"🧠 Evaluating {repo.name} ...")
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"num_ctx": 9000, "temperature": 0.01}
    )

    raw_output = response.get("message", {}).get("content", "")
    print(f"🤖 Raw model output (first 300 chars):\n{raw_output[:300]}")

    try:
        parsed = extract_json(raw_output)
    except Exception as e:
        print(f"❌ JSON parse error for {repo.name}: {e}")
        return {
            "model": MODEL,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "done": False,
            "error": str(e),
            "repo_name": repo.name,
            "raw_output": raw_output
        }

    # Build the structured content block
    content = {
        "summary": parsed.get("summary", ""),
        "overview": [
            f"Tech Stack: {parsed.get('tech_stack', '')}"
        ],
        "improvements": [s.strip() for s in parsed.get("improvements", "").split(",") if s.strip()],
        "rubric_score": {
            "feature_completion": parsed.get("feature_completion", 0),
            "functionality": parsed.get("functionality", 0),
            "ui_ux_interactivity": parsed.get("ui_ux_interactivity", 0),
            "code_quality": parsed.get("code_quality", 0),
            "error_handling": parsed.get("error_handling", 0),
            "best_practices": parsed.get("best_practices", 0),
            "tech_stack_depth": parsed.get("tech_stack_depth", 0),
            "github_usage": parsed.get("github_usage", 0),
            "uniqueness_innovation": parsed.get("uniqueness_innovation", 0),
            "ai_generated_score": parsed.get("ai_generated_score", 0),
            "total_score": parsed.get("total_score", 0)
        },
        "score_explanation": {}
    }

    # Split score_explanation into readable dict
    if isinstance(parsed.get("score_explanation"), str):
        parts = [p.strip() for p in parsed["score_explanation"].split(";") if p.strip()]
        metric_keys = [
            "feature_completion", "functionality", "ui_ux_interactivity", "code_quality",
            "error_handling", "best_practices", "tech_stack_depth", "github_usage",
            "uniqueness_innovation", "ai_generated_score"
        ]
        for i, part in enumerate(parts[:len(metric_keys)]):
            content["score_explanation"][metric_keys[i]] = part

    result = {
        "model": MODEL,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "done": True,
        "done_reason": "stop",
        "message": {
            "role": "assistant",
            "content": content
        },
        "repo_name": repo.name,
        "last_commit": get_last_commit(repo)
    }

    return result

# ---------------- MAIN ----------------
def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if not ROOT.exists():
        print(f"❌ Folder not found: {ROOT}")
        return

    for student in [s for s in ROOT.iterdir() if s.is_dir() and s.name not in IGNORE_DIRS]:
        for repo in [p for p in student.iterdir() if p.is_dir() and p.name not in IGNORE_DIRS]:
            result = evaluate_repo(repo)
            out_file = OUTPUTS_DIR / f"{student.name}_{repo.name}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved structured JSON → {out_file}")

if __name__ == "__main__":
    main()
# !/usr/bin/env python3
"""
Evaluate student project repos with your existing prompt (unchanged).
Saves structured, cleaned JSON per-project into outputs/<student_name>/<project_name>.json.
Performs double-clean & validation to ensure no '\n', '\\n', or markdown fences remain.
"""
# import os
# import json
# import subprocess
# import re
# from pathlib import Path
# from datetime import datetime
# import ollama

# # ---------------- CONFIG ----------------
# ROOT = Path(os.environ.get("REPOS_ROOT", str(Path(__file__).resolve().parent / "cloned_repos")))
# OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"   # Main output folder (as requested)
# MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b")

# IGNORE_DIRS = {
#     '.git', 'node_modules', '__pycache__', 'dist', 'build', '.idea', '.next',
#     'out', 'target', 'vendor', 'venv', '.venv', '.DS_Store'
# }

# CODE_EXT = {
#     '.py', '.js', '.ts', '.jsx', '.tsx',
#     '.java', '.cpp', '.c', '.go', '.rs',
#     '.html', '.css', '.json', '.php', '.rb', '.kt'
# }

# # Keep your exact evaluation prompt unchanged
# from textwrap import dedent
# PROMPT_TEMPLATE = dedent("""
# You are a professional software evaluator grading a second-year CSE student's project.

# Your task is to analyze ONLY the code and README provided below. Do NOT assume missing features or context. 
# Grade **strictly** based on evidence in the project itself. Do not be lenient or generous.

# OUTPUT FORMAT:
# Return a single **valid JSON object only**, no markdown, no extra text, no explanations.

# The JSON must have exactly the following structure:

# {
#   "rubric_score": {
#     "feature_completion": 0–10,
#     "functionality": 0–10,
#     "ui_ux_interactivity": 0–10,
#     "code_quality": 0–10,
#     "error_handling": 0–10,
#     "best_practices": 0–10,
#     "tech_stack_depth": 0–10,
#     "github_usage": 0–10,
#     "uniqueness_innovation": 0–10,
#     "ai_generated_score": 0–10,
#     "total_score": 0–100
#   },
#   "summary": "Two concise sentences summarizing the evaluation outcome."
# }

# EVALUATION RULES:
# - **feature_completion (0–10):** Score only if clear features are implemented. Missing endpoints, unfinished flows, or incomplete modules = lower score.
# - **functionality (0–10):** Must compile/run logically. Broken routing, undefined refs, or missing handlers = 3 or below.
# - **ui_ux_interactivity (0–10):** Only visible interactive UI elements count. Plain console or minimal HTML = 0–3.
# - **code_quality (0–10):** Judge naming, structure, indentation, duplication, and readability.
# - **error_handling (0–10):** Deduct heavily if no try/except, validation, or fallback handling.
# - **best_practices (0–10):** Use of environment configs, modular design, and separation of concerns.
# - **tech_stack_depth (0–10):** Consider depth of libraries/frameworks used beyond basics.
# - **github_usage (0–10):** Check commits, branches, and repo hygiene (README, .gitignore).
# - **uniqueness_innovation (0–10):** Score higher only for novel logic or distinct design.
# - **ai_generated_score (0–10):** 10 = clearly human-authored code; 0 = highly AI-generated or templated.
# - **total_score = sum of all 10 metrics (0–100).**

# SCORING STRICTNESS:
# - Lack of evidence = 0.
# - Minimal or incomplete evidence = 3–4.
# - Adequate but unrefined = 5–6.
# - Strong and polished = 7–8.
# - Exceptional and verified = 9–10.
# Never assume functionality not visible in code.

# PROJECT CODE (trimmed excerpts):
# {project_info}

# Now produce only the final JSON object as per the exact format above.

# """)

# # ---------------- HELPERS ----------------

# def get_last_commit(repo: Path):
#     try:
#         cmd = ["git", "-C", str(repo), "log", "-1", "--format=%cd"]
#         return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip() or "Unknown"
#     except Exception:
#         return "Unknown"

# def collect_project_info(repo: Path) -> str:
#     """
#     Collect README and top code files (largest first), concatenated into a text block.
#     """
#     chunks = []
#     readme = repo / "README.md"
#     if readme.exists():
#         try:
#             chunks.append("README.md:\n" + readme.read_text(errors="ignore")[:8000])
#         except Exception:
#             pass

#     code_files = []
#     for root, dirs, files in os.walk(repo):
#         dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
#         # avoid walking into ignored segments
#         if any(seg in IGNORE_DIRS for seg in Path(root).parts):
#             continue
#         for file in files:
#             p = Path(root) / file
#             if p.suffix.lower() in CODE_EXT:
#                 try:
#                     if p.stat().st_size < 200000:
#                         code_files.append(p)
#                 except Exception:
#                     pass

#     # sort by size descending (bigger files likely more informative)
#     code_files.sort(key=lambda f: f.stat().st_size if f.exists() else 0, reverse=True)
#     total_chars = 0
#     for f in code_files[:40]:
#         try:
#             text = f.read_text(errors="ignore")[:10000]
#             chunks.append(f"\nFILE: {f.relative_to(repo)}\n{text}")
#             total_chars += len(text)
#             if total_chars > 60000:
#                 break
#         except Exception:
#             continue

#     combined = "\n\n".join(chunks)
#     print(f"📌 DEBUG — Extracted {len(combined)} chars from {repo.name}")
#     return combined[:60000]

# def remove_markdown_and_escapes(s: str) -> str:
#     """
#     Remove markdown fences and replace escaped/newline sequences with spaces.
#     """
#     if not isinstance(s, str):
#         return s
#     out = re.sub(r"```(?:json)?", "", s, flags=re.IGNORECASE)   # remove ```json and ```
#     out = re.sub(r"```", "", out)
#     # replace literal two-character sequences like backslash-n with space,
#     # and also real newline characters.
#     out = out.replace("\\n", " ").replace("\\r", " ").replace("\r", " ").replace("\n", " ")
#     # collapse multiple spaces
#     out = re.sub(r"\s{2,}", " ", out).strip()
#     return out

# def clean_json_output(output: str) -> str:
#     """
#     First-pass cleaning: remove markdown fences, unescape newline sequences,
#     collapse whitespace. Returns cleaned string.
#     """
#     if output is None:
#         return ""
#     cleaned = remove_markdown_and_escapes(output)
#     # also remove stray escape sequences like \t
#     cleaned = cleaned.replace("\\t", " ")
#     cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
#     return cleaned

# def parse_json_from_model(output: str) -> dict:
#     """
#     Attempt to parse a JSON object from model output after cleaning.
#     Uses a few heuristics to handle trailing commas and arrays.
#     """
#     cleaned = clean_json_output(output)
#     # find outermost {...}
#     start = cleaned.find("{")
#     end = cleaned.rfind("}")
#     if start == -1 or end == -1 or end <= start:
#         raise ValueError("No JSON object braces found after cleaning.")
#     candidate = cleaned[start:end+1]
#     # try direct parse
#     try:
#         return json.loads(candidate)
#     except Exception:
#         # attempt to fix common issues: trailing commas
#         candidate_fixed = re.sub(r",\s*}", "}", candidate)
#         candidate_fixed = re.sub(r",\s*]", "]", candidate_fixed)
#         # ensure escaped quotes are properly represented - here we assume model returned strings escaped already
#         try:
#             return json.loads(candidate_fixed)
#         except Exception as e:
#             raise ValueError(f"JSON parse failed after fixes: {e}\nCandidate start:\n{candidate_fixed[:1000]}") from e

# def deep_clean_content_dict(obj):
#     """
#     Recursively walk a dict/list/str and clean any string values from newline/escape/markdown junk.
#     Returns a cleaned copy.
#     """
#     if isinstance(obj, dict):
#         return {k: deep_clean_content_dict(v) for k, v in obj.items()}
#     if isinstance(obj, list):
#         return [deep_clean_content_dict(v) for v in obj]
#     if isinstance(obj, str):
#         return remove_markdown_and_escapes(obj)
#     return obj

# def validate_saved_json(path: Path) -> bool:
#     """
#     Load the saved file and run a couple of checks:
#      - valid JSON
#      - ensure no literal sequences '\n' or '\\n' remain in any string values
#     Returns True if everything is clean/valid.
#     """
#     try:
#         data = json.loads(path.read_text(encoding="utf-8"))
#     except Exception as e:
#         print(f"❌ Validation: JSON load failed for {path}: {e}")
#         return False

#     # recursively check strings for forbidden sequences
#     def check_no_escapes(x):
#         if isinstance(x, dict):
#             return all(check_no_escapes(v) for v in x.values())
#         if isinstance(x, list):
#             return all(check_no_escapes(v) for v in x)
#         if isinstance(x, str):
#             # look for literal backslash-n sequences or actual newline chars
#             if "\\n" in x or "\\r" in x or "\n" in x or "\r" in x:
#                 return False
#             # also check for markdown fences
#             if "```" in x:
#                 return False
#             return True
#         return True

#     ok = check_no_escapes(data)
#     if not ok:
#         print(f"❌ Validation: found escape/newline or markdown fence sequences in {path}")
#     return ok

# # ---------------- CORE EVALUATION ----------------

# def build_structured_content_from_parsed(parsed: dict) -> dict:
#     """
#     Given parsed model JSON (which follows your original schema),
#     build the requested structured message.content:
#       {
#         "summary": ...,
#         "overview": [...],
#         "improvements": [...],
#         "rubric_score": {...},
#         "score_explanation": {...}
#       }
#     This function is defensive: if fields are missing it keeps empty strings/lists/numbers.
#     """
#     # parsed is expected to be a dict following your original OUTPUT JSON schema
#     summary = parsed.get("summary", "") if isinstance(parsed.get("summary", ""), str) else ""
#     tech_stack = parsed.get("tech_stack", "")
#     # improvements in your schema might be comma-separated; normalize to list
#     raw_improv = parsed.get("improvements", "")
#     if isinstance(raw_improv, str):
#         improvements = [s.strip() for s in raw_improv.split(",") if s.strip()]
#     elif isinstance(raw_improv, list):
#         improvements = raw_improv
#     else:
#         improvements = []

#     # rubric fields (default to 0)
#     rubric_keys = [
#         "feature_completion", "functionality", "ui_ux_interactivity", "code_quality",
#         "error_handling", "best_practices", "tech_stack_depth", "github_usage",
#         "uniqueness_innovation", "ai_generated_score"
#     ]
#     rubric_score = {}
#     total = 0
#     for k in rubric_keys:
#         val = parsed.get(k, 0)
#         try:
#             ival = int(val)
#         except Exception:
#             ival = 0
#         rubric_score[k] = ival
#         total += ival
#     rubric_score["total_score"] = int(parsed.get("total_score", total))

#     # score_explanation: if provided as single-line string, try split by ';'
#     score_expl = {}
#     raw_expl = parsed.get("score_explanation", "")
#     if isinstance(raw_expl, str):
#         parts = [p.strip() for p in raw_expl.split(";") if p.strip()]
#         for i, k in enumerate(rubric_keys):
#             score_expl[k] = parts[i] if i < len(parts) else ""
#     elif isinstance(raw_expl, dict):
#         for k in rubric_keys:
#             score_expl[k] = raw_expl.get(k, "")
#     else:
#         for k in rubric_keys:
#             score_expl[k] = ""

#     overview = []
#     if tech_stack:
#         overview.append(f"Tech Stack: {tech_stack}")
#     # optionally include additional fields from parsed if present
#     # e.g., strengths field could be added as a line
#     strengths = parsed.get("strengths", "")
#     if isinstance(strengths, str) and strengths.strip():
#         overview.append(f"Strengths: {strengths.strip()}")

#     content = {
#         "summary": summary,
#         "overview": overview,
#         "improvements": improvements,
#         "rubric_score": rubric_score,
#         "score_explanation": score_expl
#     }

#     # deep-clean all strings inside content
#     content = deep_clean_content_dict(content)
#     return content

# def evaluate_repo(repo: Path) -> dict:
#     info = collect_project_info(repo)
#     prompt = PROMPT_TEMPLATE.replace("{project_info}", info)

#     print(f"🧠 Evaluating {repo.name} ...")
#     response = ollama.chat(
#         model=MODEL,
#         messages=[{"role": "user", "content": prompt}],
#         options={"num_ctx": 9000, "temperature": 0.01}
#     )

#     raw_output = response.get("message", {}).get("content", "")
#     print(f"🤖 Raw output sample ({repo.name}):\n{(raw_output or '')[:400]}")

#     # parse model output into dict (cleaning happens inside)
#     try:
#         parsed = parse_json_from_model(raw_output)
#     except Exception as e:
#         print(f"❌ Failed to parse model JSON for {repo.name}: {e}")
#         return {
#             "model": MODEL,
#             "created_at": datetime.utcnow().isoformat() + "Z",
#             "done": False,
#             "error": str(e),
#             "raw_output": raw_output,
#             "repo_name": repo.name
#         }

#     # Build the clean structured message.content block
#     content = build_structured_content_from_parsed(parsed)

#     result = {
#         "model": MODEL,
#         "created_at": datetime.utcnow().isoformat() + "Z",
#         "done": True,
#         "done_reason": "stop",
#         "message": {
#             "role": "assistant",
#             "content": content
#         },
#         "repo_name": repo.name,
#         "last_commit": get_last_commit(repo)
#     }

#     return result

# # ---------------- MAIN ----------------

# def main():
#     OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
#     if not ROOT.exists():
#         print(f"❌ Folder not found: {ROOT.resolve()}")
#         return

#     students = [s for s in ROOT.iterdir() if s.is_dir() and s.name not in IGNORE_DIRS]
#     print(f"✅ Students found: {[s.name for s in students]}")

#     for student in students:
#         student_out_dir = OUTPUTS_DIR / student.name
#         student_out_dir.mkdir(parents=True, exist_ok=True)

#         projects = [p for p in student.iterdir() if p.is_dir() and p.name not in IGNORE_DIRS]
#         print(f"\n👤 Student: {student.name} — Projects: {[p.name for p in projects]}")

#         for repo in projects:
#             print(f"\n🚀 Evaluating {student.name}/{repo.name}")
#             result = evaluate_repo(repo)

#             # --- Ensure full path exists before saving ---
#             student_out_dir.mkdir(parents=True, exist_ok=True)
#             out_file = student_out_dir / f"{repo.name}.json"
#             out_file.parent.mkdir(parents=True, exist_ok=True)

#             print(f"💾 Writing JSON file → {out_file}")
#             with open(out_file, "w", encoding="utf-8") as f:
#                 json.dump(result, f, ensure_ascii=False, indent=2)

#             # --- Validate and clean ---
#             valid = validate_saved_json(out_file)
#             if not valid:
#                 print(f"🔁 Re-cleaning and re-saving {out_file}")
#                 try:
#                     data = json.loads(out_file.read_text(encoding="utf-8"))
#                     if "message" in data and isinstance(data["message"], dict):
#                         content = data["message"].get("content", {})
#                         cleaned_content = deep_clean_content_dict(content)
#                         data["message"]["content"] = cleaned_content
#                     else:
#                         data = deep_clean_content_dict(data)
#                     out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
#                 except Exception as e:
#                     print(f"❌ Re-clean/resave failed for {out_file}: {e}")

#                 valid2 = validate_saved_json(out_file)
#                 if not valid2:
#                     print(f"❌ Final validation failed for {out_file}. Please inspect manually.")
#                 else:
#                     print(f"✅ Final validation OK for {out_file}")
#             else:
#                 print(f"✅ Saved and validated → {out_file}")

#     print("\n🎉 All evaluations complete. Outputs are in:", OUTPUTS_DIR.resolve())


# if __name__ == "__main__":
#     main()
