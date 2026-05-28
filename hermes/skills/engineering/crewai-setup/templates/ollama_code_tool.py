"""Ollama-native CrewAI tool template — starter for local LLM coding tools.

Copy this file and customize:
1. Set OLLAMA_BASE and DEFAULT_MODEL
2. Add/remove tools in FILE_TOOLS and TOOL_MAP
3. Adjust SYSTEM_PROMPT for your use case
4. Set max_turns for your model's patience

The text-embedded tool call parser handles models that output
function calls in text (e.g., laguna) instead of structured JSON.
Fuzzy matching corrects common typos in tool names.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ── Configuration ────────────────────────────────────────────────────

OLLAMA_BASE = "http://100.84.92.74:11434"
DEFAULT_MODEL = "laguna-xs.2:128k"
DEFAULT_WORKDIR = str(Path.home())

# ── Tool definitions ─────────────────────────────────────────────────

FILE_TOOLS = [
    # Add your tool definitions here. Example:
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and return its content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        },
    },
    # ... add more tools
]

TOOL_MAP = {
    "read_file": lambda path, wd: f"Content of {path}",
    # ... add handlers
}

SYSTEM_PROMPT = """You are a coding assistant with file tools."""


class OllamaCodeTool(BaseTool):
    """Your tool description here."""
    name: str = "ollama_code"
    description: str = "Execute coding tasks via local Ollama model."

    def _call_api(self, messages: list[dict], model: str) -> dict:
        body = json.dumps({
            "model": model,
            "messages": messages,
            "tools": FILE_TOOLS,
            "stream": False,
            "options": {"num_ctx": 65536},
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())

    def _run(self, task: str, model: str = "", workdir: str = "") -> str:
        model = model or DEFAULT_MODEL
        workdir = workdir or DEFAULT_WORKDIR
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}"},
        ]
        for turn in range(15):
            resp = self._call_api(messages, model)
            msg = resp.get("message", {})
            content = msg.get("content", "").strip()
            tool_calls = msg.get("tool_calls", [])

            # Try text-embedded tool calls first
            text_tools = _parse_text_tool_calls(content)
            if text_tools:
                messages.append(msg)
                results = []
                for name, args in text_tools:
                    name = _fuzzy_tool(name)
                    handler = TOOL_MAP.get(name)
                    result = handler(**args, wd=workdir) if handler else f"Unknown: {name}"
                    results.append(f"[{name}]: {result}")
                messages.append({"role": "tool", "content": "\n".join(results)})
                continue

            # Pure text response — done
            if content and not tool_calls:
                return content

            # Structured tool calls
            if tool_calls:
                messages.append(msg)
                results = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = _fuzzy_tool(fn.get("name", ""))
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args) if args else {}
                    handler = TOOL_MAP.get(name)
                    result = handler(**args, wd=workdir) if handler else f"Unknown: {name}"
                    results.append(f"[{name}]: {result}")
                messages.append({"role": "tool", "content": "\n".join(results)})
                continue

            return "Empty response."
        return "Max turns exceeded."


# ── Text-embedded tool call parser ───────────────────────────────────

def _parse_text_tool_calls(text: str) -> list[tuple[str, dict]]:
    """Extract func({"key":"val"}) patterns from text."""
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(\{[^}]+\})\s*\)'
    results = []
    for name, json_args in re.findall(pattern, text):
        try:
            args = json.loads(json_args)
            if isinstance(args, dict):
                results.append((name, args))
        except json.JSONDecodeError:
            try:
                args = json.loads(json_args.replace("'", '"'))
                if isinstance(args, dict):
                    results.append((name, args))
            except json.JSONDecodeError:
                pass
    return results


def _fuzzy_tool(name: str) -> str:
    """Correct common typos in tool names."""
    if name in TOOL_MAP:
        return name
    TYPOS = {
        "ist_files": "list_files",
        "wrtie_file": "write_file",
        "exec_command": "run_command",
        "execute": "run_command",
    }
    if name in TYPOS:
        return TYPOS[name]
    for valid in TOOL_MAP:
        if valid[:4] == name[:4]:
            return valid
    return name
