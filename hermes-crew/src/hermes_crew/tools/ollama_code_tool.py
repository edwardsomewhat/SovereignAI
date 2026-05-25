"""Direct Ollama chat tool for CrewAI — raw API, no compatibility layer.

Bypasses OpenCode's @ai-sdk/openai-compatible issues with large local models.
Calls Ollama's native /api/chat endpoint with tool support.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OLLAMA_BASE = os.getenv("OLLAMA_HQ", "http://100.84.92.74:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_CODE_MODEL", "laguna-xs.2:128k")
DEFAULT_WORKDIR = os.getenv("OLLAMA_CODE_WORKDIR", str(Path.home()))


class OllamaCodeInput(BaseModel):
    task: str = Field(description="Detailed coding task to perform.")
    model: str = Field(default="", description="Model name. Empty = default.")
    workdir: str = Field(default="", description="Working directory. Empty = $HOME.")


# ── File tools the model can call ────────────────────────────────────

def _read_file(path: str, workdir: str) -> str:
    """Read a file, return its content with line numbers."""
    full = Path(workdir) / path if not Path(path).is_absolute() else Path(path)
    try:
        lines = full.read_text().splitlines()
        numbered = "\n".join(f"{i+1:4d}|{l}" for i, l in enumerate(lines))
        return numbered[:8000]  # cap at 8K chars
    except FileNotFoundError:
        return f"ERROR: File not found: {full}"
    except Exception as e:
        return f"ERROR: {e}"


def _write_file(path: str, content: str, workdir: str) -> str:
    """Write content to a file."""
    full = Path(workdir) / path if not Path(path).is_absolute() else Path(path)
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        return f"OK: Wrote {len(content)} bytes to {full}"
    except Exception as e:
        return f"ERROR: {e}"


def _search_files(pattern: str, path: str, workdir: str) -> str:
    """Search file contents with ripgrep."""
    import subprocess

    search_dir = Path(workdir) / path if not Path(path).is_absolute() else Path(path)
    try:
        result = subprocess.run(
            ["rg", "--max-count=50", "-n", pattern, str(search_dir)],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout[:8000] if result.stdout else "No matches found."
    except FileNotFoundError:
        return "ERROR: ripgrep (rg) not installed."
    except Exception as e:
        return f"ERROR: {e}"


def _run_command(command: str, workdir: str) -> str:
    """Execute a shell command and return output."""
    import subprocess

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=30, cwd=workdir
        )
        out = result.stdout[:4000]
        if result.stderr:
            out += f"\n[stderr]:\n{result.stderr[:1000]}"
        return out or f"Exit code: {result.returncode}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out (30s)"
    except Exception as e:
        return f"ERROR: {e}"


def _list_files(path: str, workdir: str) -> str:
    """List files in a directory."""
    d = Path(workdir) / path if not Path(path).is_absolute() else Path(path)
    try:
        entries = sorted(d.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        lines = []
        for e in entries[:50]:
            suffix = "/" if e.is_dir() else f" ({e.stat().st_size}B)"
            lines.append(f"  {e.name}{suffix}")
        return "\n".join(lines) if lines else "(empty)"
    except FileNotFoundError:
        return f"ERROR: Directory not found: {d}"
    except Exception as e:
        return f"ERROR: {e}"


# ── Docker & web tools ────────────────────────────────────────────────

SEARXNG_URL = "http://100.71.6.98:8080"


def _web_search(query: str, workdir: str = "") -> str:
    """Search the web via local SearXNG instance."""
    import urllib.request
    import urllib.parse
    try:
        url = f"{SEARXNG_URL}/search?q={urllib.parse.quote(query)}&format=json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results", [])[:5]
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results):
            lines.append(f"{i+1}. {r.get('title', '?')}")
            lines.append(f"   {r.get('url', '?')}")
            lines.append(f"   {r.get('content', '')[:200]}")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: web_search failed: {e}"


def _docker_pull(image: str, workdir: str = "") -> str:
    """Pull a Docker image."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "pull", image],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout[-2000:] or result.stderr[-2000:] or "Pull complete."
    except subprocess.TimeoutExpired:
        return "ERROR: docker pull timed out (120s)"
    except FileNotFoundError:
        return "ERROR: docker not installed or not in PATH"
    except Exception as e:
        return f"ERROR: docker pull failed: {e}"


def _docker_run(image: str, name: str, ports: str, volumes: str,
                env_vars: str, workdir: str = "") -> str:
    """Run a Docker container. ports like '8080:80', volumes like '/host:/container'."""
    import subprocess, shlex
    cmd = ["docker", "run", "-d", "--name", name]
    if ports:
        for p in ports.split(","):
            cmd += ["-p", p.strip()]
    if volumes:
        for v in volumes.split(","):
            cmd += ["-v", v.strip()]
    if env_vars:
        for e in env_vars.split(","):
            cmd += ["-e", e.strip()]
    cmd.append(image)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return f"OK: Container '{name}' started ({result.stdout.strip()[:12]})"
        return f"ERROR: {result.stderr.strip()[:500]}"
    except FileNotFoundError:
        return "ERROR: docker not installed"
    except Exception as e:
        return f"ERROR: {e}"


# ── Tool registry ────────────────────────────────────────────────────

FILE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and return its content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path (relative or absolute)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Full file content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search file contents with regex pattern (ripgrep).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory to search in"},
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information, packages, libraries, or solutions. Use this to find existing Docker images, pip packages, or documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_pull",
            "description": "Pull a Docker image from a registry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image": {"type": "string", "description": "Docker image name (e.g. 'python:3.11-slim')"},
                },
                "required": ["image"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_run",
            "description": "Run a Docker container. Use comma-separated strings for multiple ports/volumes/env vars.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image": {"type": "string", "description": "Docker image to run"},
                    "name": {"type": "string", "description": "Container name"},
                    "ports": {"type": "string", "description": "Port mappings, e.g. '8080:80,7001:7001'"},
                    "volumes": {"type": "string", "description": "Volume mappings, e.g. '/host/path:/container/path'"},
                    "env_vars": {"type": "string", "description": "Environment vars, e.g. 'KEY=val,KEY2=val2'"},
                },
                "required": ["image", "name"],
            },
        },
    },
]

TOOL_MAP = {
    "read_file": _read_file,
    "write_file": _write_file,
    "search_files": _search_files,
    "run_command": _run_command,
    "list_files": _list_files,
    "web_search": _web_search,
    "docker_pull": _docker_pull,
    "docker_run": _docker_run,
}

SYSTEM_PROMPT = """You are a senior software engineer. You have access to tools:
- read_file(path) — read a file
- write_file(path, content) — create/overwrite a file
- search_files(pattern, path) — grep for a pattern
- run_command(command) — run a shell command
- list_files(path) — list directory contents
- web_search(query) — search the web for packages, images, docs, solutions
- docker_pull(image) — pull a Docker image
- docker_run(image, name, ports, volumes, env_vars) — run a container

CRITICAL: Use tools IMMEDIATELY. Do not plan, do not reason, do not explain what you will do.
Just do it — call write_file or web_search NOW. Explain only AFTER the code is written and tested.

When asked to build something:
1. First, web_search for existing solutions, Docker images, or pip packages
2. If you find something: docker_pull it, write a compose file, docker_run it
3. If building from scratch: IMMEDIATELY write_file to create the code
4. Then run_command to test it
5. Only then, briefly summarize what you built

NEVER spend a turn just thinking or planning. Every single turn must include at least one tool call.
Keep responses under 3 sentences — use tools for everything else."""


class OllamaCodeTool(BaseTool):
    """Execute coding tasks via Ollama's native chat API with file tools."""

    name: str = "ollama_code"
    description: str = (
        "Execute a coding task using a local LLM via Ollama's native API. "
        "The model can read, write, search, and run commands. "
        "Use this for code implementation, refactoring, and debugging."
    )
    args_schema: type[BaseModel] = OllamaCodeInput

    def _call_api(self, messages: list[dict], model: str) -> dict:
        """Call Ollama /api/chat and return the response."""
        body = json.dumps({
            "model": model,
            "messages": messages,
            "tools": FILE_TOOLS,
            "stream": False,
            "options": {"num_ctx": 65536, "num_predict": 1024},
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    def _run(self, task: str, model: str = "", workdir: str = "") -> str:
        model = model or DEFAULT_MODEL
        workdir = workdir or DEFAULT_WORKDIR

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Working directory: {workdir}\n\nTask: {task}"},
        ]

        max_turns = 25
        for turn in range(max_turns):
            resp = self._call_api(messages, model)

            if "error" in resp:
                return f"Ollama API error: {resp['error']}"

            msg = resp.get("message", {})
            content = msg.get("content", "").strip()
            tool_calls = msg.get("tool_calls", [])

            # Try text-embedded tool calls first (laguna, some local models)
            text_tools = _parse_text_tool_calls(content)
            if text_tools:
                messages.append(msg)
                tool_results = []
                for name, args in text_tools:
                    name = _fuzzy_tool(name)
                    handler = TOOL_MAP.get(name)
                    if handler:
                        result = _dispatch_tool(handler, name, args, workdir)
                    else:
                        result = f"Unknown tool: {name}"
                    tool_results.append(f"[{name}]: {result}")
                messages.append({
                    "role": "tool",
                    "content": "\n\n".join(tool_results),
                })
                continue

            # Model responded with text only — done
            if content and not tool_calls:
                return content

            # Structured tool calls (nemotron3, granite)
            if tool_calls:
                # Check if tool_calls are valid (not empty stubs)
                valid = any(
                    tc.get("function", {}).get("name", "")
                    for tc in tool_calls
                )
                if not valid:
                    # Garbage tool calls with no name — treat as text response
                    return content if content else "Model returned empty tool calls."

                messages.append(msg)
                tool_results = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments", {})

                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}

                    name = _fuzzy_tool(name)
                    handler = TOOL_MAP.get(name)
                    if handler:
                        result = _dispatch_tool(handler, name, args, workdir)
                    else:
                        result = f"Unknown tool: {name}"

                    tool_results.append(f"[{name}]: {result}")

                messages.append({
                    "role": "tool",
                    "content": "\n\n".join(tool_results),
                })
                continue

            # Model sent empty message
            return "Model returned empty response."

        return f"Max turns ({max_turns}) exceeded without completion."


# ── Text-embedded tool call parser (for laguna & models with broken JSON tools) ──

def _parse_text_tool_calls(text: str) -> list[tuple[str, dict]]:
    """Extract function calls from text like: name({"key": "val"}).

    Returns list of (tool_name, args_dict) tuples. Empty if no calls found.
    """
    import re

    # Match: function_name({"key": "value", ...})  or  func_name({...})
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(\{[^}]+\})\s*\)'
    matches = re.findall(pattern, text)

    results = []
    for name, json_args in matches:
        try:
            args = json.loads(json_args)
            if isinstance(args, dict):
                results.append((name, args))
        except json.JSONDecodeError:
            # Try with single-quoted keys
            try:
                fixed = json_args.replace("'", '"')
                args = json.loads(fixed)
                if isinstance(args, dict):
                    results.append((name, args))
            except json.JSONDecodeError:
                pass

    return results


def _fuzzy_tool(name: str) -> str:
    """Fuzzy-match tool names to handle typos (e.g. 'ist_files' → 'list_files')."""
    # Direct match
    if name in TOOL_MAP:
        return name

    # Known typos
    TYPO_MAP = {
        "ist_files": "list_files",
        "ls_files": "list_files",
        "list_file": "list_files",
        "write_file": "write_file",
        "wrtie_file": "write_file",
        "read_file": "read_file",
        "raed_file": "read_file",
        "search_files": "search_files",
        "serch_files": "search_files",
        "run_command": "run_command",
        "rnu_command": "run_command",
        "exec_command": "run_command",
        "execute": "run_command",
        "websearch": "web_search",
        "web_search": "web_search",
        "search_web": "web_search",
        "dockerpull": "docker_pull",
        "pull_docker": "docker_pull",
        "dockerrun": "docker_run",
        "run_docker": "docker_run",
        "start_container": "docker_run",
    }
    if name in TYPO_MAP:
        return TYPO_MAP[name]

    # Fallback: substring match
    for valid in TOOL_MAP:
        if valid[:4] == name[:4] or name[:4] == valid[:4]:
            return valid

    return name


def _dispatch_tool(handler, name: str, args: dict, workdir: str) -> str:
    """Route tool call to the right handler with correct argument mapping."""
    if name == "read_file":
        return handler(args.get("path", ""), workdir)
    elif name == "write_file":
        return handler(args.get("path", ""), args.get("content", ""), workdir)
    elif name == "list_files":
        return handler(args.get("path", "."), workdir)
    elif name == "search_files":
        return handler(args.get("pattern", ""), args.get("path", "."), workdir)
    elif name == "run_command":
        return handler(args.get("command", ""), workdir)
    elif name == "web_search":
        return handler(args.get("query", ""), workdir)
    elif name == "docker_pull":
        return handler(args.get("image", ""), workdir)
    elif name == "docker_run":
        return handler(
            args.get("image", ""), args.get("name", ""),
            args.get("ports", ""), args.get("volumes", ""),
            args.get("env_vars", ""), workdir
        )
    return f"Unknown tool: {name}"
