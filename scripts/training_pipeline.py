#!/usr/bin/env python3
"""Sovereign Training Pipeline — session capture, summarization, and grading.

Three stages:
  1. CAPTURE: Scan Hermes sessions, extract new ones, save as text to raw/
  2. SUMMARIZE: Process raw/ files via local LLM into 5-field template, save to processed/
  3. GRADE: Score processed/ entries, keep A/B in curated/, delete C/D

Usage:
  python training_pipeline.py capture    # Stage 1: extract new sessions
  python training_pipeline.py summarize  # Stage 2: summarize raw files
  python training_pipeline.py grade      # Stage 3: grade and filter
  python training_pipeline.py all        # Run all stages
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

HOME = Path.home()
HERMES_DIR = HOME / ".hermes"
SESSIONS_DIR = HERMES_DIR / "sessions"
TRAINING_DIR = HERMES_DIR / "training_data"
RAW_DIR = TRAINING_DIR / "raw"
PROCESSED_DIR = TRAINING_DIR / "processed"
CURATED_DIR = TRAINING_DIR / "curated"
STATE_FILE = TRAINING_DIR / "pipeline_state.json"

# Template for summaries
TEMPLATE = """INTERACTION:  [debug | architecture | implementation | correction | discovery]
SUBJECT:      [one-line description]
CONFLICT:     [what was broken, unknown, or blocked]
RESOLUTION:   [what fixed it, with specifics]
RATIONALE:    [why this approach — tie to Sovereign Codex principle]"""

# Grading rubric
RUBRIC = """Score each training example A, B, C, or D:

A (keep): User correction + agent adapts. Novel problem solved. Architecture decision made.
B (keep): Multi-turn reasoning chain with tool calls that succeeded. Non-trivial workflow.
C (discard): Mechanical success. File reads, simple queries. Single tool calls.
D (discard): Failures, dead ends, agent spinning with no resolution.

Return ONLY the letter grade (A, B, C, or D)."""

# Local LLM endpoint (change to your Ollama/HQ IP)
LLM_URL = os.environ.get("TRAINING_LLM_URL", "http://100.84.92.74:11434")
LLM_MODEL = os.environ.get("TRAINING_LLM_MODEL", "qwen3.5:9b")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_session_ts": None, "sessions_processed": 0}


def save_state(state):
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_session_text(session_path):
    """Convert a Hermes session JSON to a clean text transcript."""
    data = json.loads(Path(session_path).read_text())
    lines = []
    lines.append(f"# Session: {data.get('session_id', 'unknown')}")
    lines.append(f"Model: {data.get('model', '?')} | Platform: {data.get('platform', '?')}")
    lines.append(f"Started: {data.get('session_start', '?')}")
    lines.append(f"Messages: {data.get('message_count', 0)}")
    lines.append("")

    for msg in data.get("messages", []):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        
        # Truncate long tool outputs to prevent flooding
        if role == "tool" and len(str(content)) > 500:
            content = str(content)[:500] + "\n... [tool output truncated]"
        
        lines.append(f"## {role.upper()}")
        lines.append(str(content))
        lines.append("")

    return "\n".join(lines)


def call_ollama(prompt, system=None):
    """Call local Ollama model."""
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1024}
    }
    if system:
        payload["system"] = system
    
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{LLM_URL}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        return result.get("response", "").strip()
    except Exception as e:
        return f"LLM_ERROR: {e}"


def stage_capture():
    """Stage 1: Extract new sessions to raw/."""
    state = load_state()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    sessions = sorted(SESSIONS_DIR.glob("session_*.json"))
    new_count = 0
    
    for sp in sessions:
        # Check if already processed
        session_id = sp.stem
        raw_file = RAW_DIR / f"{session_id}.md"
        if raw_file.exists():
            continue
        
        # Check timestamp
        mtime = sp.stat().st_mtime
        if state["last_session_ts"] and mtime <= state["last_session_ts"]:
            continue
        
        # Extract and save
        text = extract_session_text(sp)
        raw_file.write_text(text)
        new_count += 1
        print(f"  Captured: {session_id}")
    
    if new_count:
        state["last_session_ts"] = time.time()
        state["sessions_processed"] = state.get("sessions_processed", 0) + new_count
        save_state(state)
        print(f"Captured {new_count} new sessions -> {RAW_DIR}")
    else:
        print("No new sessions to capture.")


def stage_summarize():
    """Stage 2: Summarize raw files into 5-field template."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    system_prompt = """You are a training data curator for the Sovereign AI project. 
Your job is to read agent session transcripts and extract exactly ONE training example 
per session using this template:

""" + TEMPLATE + """

Rules:
- INTERACTION type must be one of: debug, architecture, implementation, correction, discovery
- SUBJECT is a single line describing what was worked on
- CONFLICT describes what was broken, unknown, or blocked
- RESOLUTION describes what fixed it with specific commands, paths, or approaches
- RATIONALE ties the approach to a Sovereign Codex principle (Build Over Buy, Local First, 
  Swappable Brain, Digital Autarky, Accuracy Over Speed, Self-Documentation, etc.)
- Be concise. Each field should be 1-3 sentences maximum.
- If the session has no clear conflict/resolution (just Q&A), mark INTERACTION as discovery 
  and describe what was learned.
- Output ONLY the filled template, no other text."""

    raw_files = sorted(RAW_DIR.glob("*.md"))
    if not raw_files:
        print("No raw files to summarize.")
        return
    
    count = 0
    for rf in raw_files:
        out_file = PROCESSED_DIR / f"{rf.stem}.txt"
        if out_file.exists():
            continue
        
        text = rf.read_text()
        # Truncate very long sessions for the 9B model
        if len(text) > 8000:
            # Keep first 2000 and last 6000 chars (most resolution at end)
            text = text[:2000] + "\n\n... [middle truncated] ...\n\n" + text[-6000:]
        
        print(f"  Summarizing: {rf.stem}...")
        summary = call_ollama(text, system_prompt)
        
        if summary.startswith("LLM_ERROR"):
            print(f"    ERROR: {summary}")
            continue
        
        out_file.write_text(summary)
        count += 1
    
    print(f"Summarized {count} raw files -> {PROCESSED_DIR}")


def stage_grade():
    """Stage 3: Grade processed files, keep A/B, delete C/D."""
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    
    system_prompt = """You are a training data quality grader for the Sovereign AI project.
    
""" + RUBRIC + """

Output ONLY the letter grade (A, B, C, or D). No explanation."""

    processed_files = sorted(PROCESSED_DIR.glob("*.txt"))
    if not processed_files:
        print("No processed files to grade.")
        return
    
    kept, deleted = 0, 0
    for pf in processed_files:
        text = pf.read_text()
        
        grade = call_ollama(text, system_prompt).strip().upper()
        
        if grade in ("A", "B"):
            dest = CURATED_DIR / pf.name
            dest.write_text(text)
            pf.unlink()
            kept += 1
            print(f"  {grade}: {pf.stem} -> curated")
        else:
            pf.unlink()
            deleted += 1
            print(f"  {grade}: {pf.stem} -> deleted")
    
    print(f"Graded: {kept} kept in {CURATED_DIR}, {deleted} deleted")


def stage_all():
    stage_capture()
    print()
    stage_summarize()
    print()
    stage_grade()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    {
        "capture": stage_capture,
        "summarize": stage_summarize,
        "grade": stage_grade,
        "all": stage_all,
    }.get(cmd, lambda: print(f"Unknown stage: {cmd}\nUse: capture | summarize | grade | all"))()
