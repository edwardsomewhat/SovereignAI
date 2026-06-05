#!/usr/bin/env python3
"""Tailscale MCP Server — exposes tailnet management tools to Hermes."""

import json
import subprocess
import os
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("tailscale-mcp")

LOCAL_API_SOCK = "/var/run/tailscale/tailscaled.sock"

def _tailscale_cli(*args: str) -> dict:
    """Run a tailscale CLI command and return parsed result."""
    cmd = ["tailscale"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "exit_code": result.returncode,
    }

def _local_api(endpoint: str) -> dict:
    """Hit the Tailscale local API via Unix socket."""
    cmd = [
        "curl", "-s", "--unix-socket", LOCAL_API_SOCK,
        f"http://local-tailscaled.sock/localapi/v0/{endpoint}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        data = json.loads(result.stdout)
        return {"ok": True, "data": data}
    except json.JSONDecodeError:
        return {"ok": False, "error": result.stdout.strip()}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="tailscale_status",
            description="Get full tailnet status — all nodes, online/offline, IPs, OS, user. Returns a compact summary table plus raw JSON.",
            inputSchema={
                "type": "object",
                "properties": {
                    "json_output": {
                        "type": "boolean",
                        "description": "Return raw JSON instead of summary (default: false)",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="tailscale_node",
            description="Get detailed info about a specific tailnet node by hostname or IP.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Node hostname or Tailscale IP (e.g. 'masogany' or '100.79.56.109')"
                    }
                },
                "required": ["hostname"]
            }
        ),
        Tool(
            name="tailscale_ssh",
            description="SSH to a tailnet node and run a command. Uses Tailscale SSH (no password needed if enabled on target).",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Node hostname or Tailscale IP"
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to run on the remote node"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                        "default": 30
                    }
                },
                "required": ["hostname", "command"]
            }
        ),
        Tool(
            name="tailscale_file_send",
            description="Send a file to another tailnet node via Taildrop.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target node hostname or IP"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to send"
                    }
                },
                "required": ["target", "file_path"]
            }
        ),
        Tool(
            name="tailscale_file_receive",
            description="List or receive files sent to this node via Taildrop.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "get"],
                        "description": "list: show waiting files; get: download all waiting files to default dir",
                        "default": "list"
                    },
                    "target_dir": {
                        "type": "string",
                        "description": "Directory to save files (only for action='get', default: ~/Downloads)",
                    }
                }
            }
        ),
        Tool(
            name="tailscale_ping",
            description="Ping a tailnet node to check connectivity and latency.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Node hostname or Tailscale IP to ping"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of pings (default: 3)",
                        "default": 3
                    }
                },
                "required": ["hostname"]
            }
        ),
        Tool(
            name="tailscale_manage",
            description="Manage Tailscale on this node — check status, see whois info, view network config.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "netcheck", "whois", "ip", "version", "up"],
                        "description": "status: full tailscale status; netcheck: NAT/network check; whois: look up a tailnet IP/user; ip: show this node's IP; version: show version; up: show current up flags"
                    },
                    "target": {
                        "type": "string",
                        "description": "Target for whois (hostname or IP)"
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="tailscale_api",
            description="Call the official Tailscale REST API (requires TAIlSCALE_API_KEY env var or TS_API_KEY). Use for ACL management, DNS settings, device approval, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PATCH", "DELETE"],
                        "description": "HTTP method",
                        "default": "GET"
                    },
                    "path": {
                        "type": "string",
                        "description": "API path (e.g. '/api/v2/tailnet/example.ts.net/devices')"
                    },
                    "body": {
                        "type": "object",
                        "description": "JSON body for POST/PATCH (optional)"
                    }
                },
                "required": ["path"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "tailscale_status":
            return await _handle_status(arguments)
        elif name == "tailscale_node":
            return await _handle_node(arguments)
        elif name == "tailscale_ssh":
            return await _handle_ssh(arguments)
        elif name == "tailscale_file_send":
            return await _handle_file_send(arguments)
        elif name == "tailscale_file_receive":
            return await _handle_file_receive(arguments)
        elif name == "tailscale_ping":
            return await _handle_ping(arguments)
        elif name == "tailscale_manage":
            return await _handle_manage(arguments)
        elif name == "tailscale_api":
            return await _handle_api(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_status(args: dict) -> list[TextContent]:
    r = _local_api("status")
    if not r["ok"]:
        cli = _tailscale_cli("status", "--json")
        if cli["ok"]:
            r = {"ok": True, "data": json.loads(cli["stdout"])}
        else:
            return [TextContent(type="text", text=f"Failed: {cli['stderr']}")]

    data = r["data"]
    if args.get("json_output"):
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    lines = ["=== TAILNET STATUS ===\n"]
    self_node = data.get("Self", {})
    lines.append(f"Self: {self_node.get('HostName')} ({', '.join(self_node.get('TailscaleIPs', []))})")
    lines.append("")

    peers = data.get("Peer", {})
    online = []; offline = []
    for k, v in peers.items():
        entry = f"  {v.get('HostName', k):25s} {v.get('OS', '?'):10s} {', '.join(v.get('TailscaleIPs', []))}"
        if v.get("Online"):
            online.append("\U0001f7e2 " + entry)
        else:
            offline.append("\u26ab " + entry)

    lines.append(f"ONLINE ({len(online)}):")
    lines.extend(online)
    if offline:
        lines.append(f"\nOFFLINE ({len(offline)}):")
        lines.extend(offline)

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_node(args: dict) -> list[TextContent]:
    hostname = args["hostname"]
    r = _local_api("status")
    if not r["ok"]:
        return [TextContent(type="text", text="Failed to get tailnet status")]

    data = r["data"]
    peers = data.get("Peer", {})

    found = None
    for k, v in peers.items():
        if (hostname.lower() in v.get("HostName", "").lower() or
            hostname in v.get("TailscaleIPs", [])):
            found = v
            break

    if not found:
        return [TextContent(type="text", text=f"Node '{hostname}' not found on tailnet")]

    whois = _tailscale_cli("whois", found.get("TailscaleIPs", ["unknown"])[0])

    return [TextContent(type="text", text=json.dumps({
        "hostname": found.get("HostName"),
        "dns_name": found.get("DNSName"),
        "os": found.get("OS"),
        "ips": found.get("TailscaleIPs", []),
        "online": found.get("Online"),
        "user": found.get("UserID"),
        "last_seen": found.get("LastSeen"),
        "exit_node": found.get("ExitNode"),
        "whois": whois["stdout"] if whois["ok"] else "unavailable"
    }, indent=2))]


async def _handle_ssh(args: dict) -> list[TextContent]:
    hostname = args["hostname"]
    command = args["command"]
    timeout = args.get("timeout", 30)

    result = subprocess.run(
        ["tailscale", "ssh", hostname, command],
        capture_output=True, text=True, timeout=timeout
    )
    return [TextContent(type="text", text=json.dumps({
        "ok": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "exit_code": result.returncode,
    }, indent=2))]


async def _handle_file_send(args: dict) -> list[TextContent]:
    target = args["target"]
    file_path = args["file_path"]
    if not os.path.exists(file_path):
        return [TextContent(type="text", text=f"File not found: {file_path}")]
    result = subprocess.run(
        ["tailscale", "file", "cp", file_path, f"{target}:"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        return [TextContent(type="text", text=f"Sent {file_path} to {target}")]
    result2 = subprocess.run(
        ["sudo", "-S", "tailscale", "file", "cp", file_path, f"{target}:"],
        input="SUDO_PASSWORD_HERE\n", capture_output=True, text=True, timeout=60
    )
    if result2.returncode == 0:
        return [TextContent(type="text", text=f"Sent {file_path} to {target} (via sudo)")]
    return [TextContent(type="text", text=f"Failed: {result.stderr}")]


async def _handle_file_receive(args: dict) -> list[TextContent]:
    action = args.get("action", "list")
    if action == "list":
        result = subprocess.run(["tailscale", "file", "get", "."], capture_output=True, text=True, timeout=10)
        if "Access denied" in result.stderr:
            result = subprocess.run(["sudo", "-S", "tailscale", "file", "get", "."], capture_output=True, text=True, timeout=10)
        return [TextContent(type="text", text=result.stdout.strip() or "(no files waiting)")]
    elif action == "get":
        target = args.get("target_dir", os.path.expanduser("~/Downloads"))
        os.makedirs(target, exist_ok=True)
        result = subprocess.run(["tailscale", "file", "get", target], capture_output=True, text=True, timeout=30)
        if "Access denied" in result.stderr:
            result = subprocess.run(["sudo", "-S", "tailscale", "file", "get", target], capture_output=True, text=True, timeout=30)
        return [TextContent(type="text", text=result.stdout.strip() or "Files downloaded")]


async def _handle_ping(args: dict) -> list[TextContent]:
    hostname = args["hostname"]
    count = args.get("count", 3)
    result = _tailscale_cli("ping", "-c", str(count), hostname)
    return [TextContent(type="text", text=result["stdout"] or result["stderr"])]


async def _handle_manage(args: dict) -> list[TextContent]:
    action = args["action"]
    target = args.get("target", "")
    cmd = ["tailscale"]
    if action == "status": cmd.append("status")
    elif action == "netcheck": cmd.append("netcheck")
    elif action == "whois": cmd.extend(["whois", target])
    elif action == "ip": cmd.append("ip")
    elif action == "version": cmd.append("version")
    elif action == "up": cmd.extend(["debug", "prefs"])
    result = _tailscale_cli(*cmd)
    return [TextContent(type="text", text=result["stdout"] or result["stderr"])]


async def _handle_api(args: dict) -> list[TextContent]:
    api_key = os.environ.get("TAILSCALE_API_KEY") or os.environ.get("TS_API_KEY")
    if not api_key:
        return [TextContent(type="text",
            text="No Tailscale API key found. Set TAIlSCALE_API_KEY or TS_API_KEY env var.\n"
                 "Get one at: https://login.tailscale.com/admin/settings/keys")]
    method = args.get("method", "GET")
    path = args["path"]
    body = args.get("body")
    base = "https://api.tailscale.com"
    url = base + path
    curl_cmd = ["curl", "-s", "-X", method, url, "-u", f"{api_key}:", "-H", "Content-Type: application/json"]
    if body and method in ("POST", "PATCH"):
        curl_cmd.extend(["-d", json.dumps(body)])
    result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
    try:
        return [TextContent(type="text", text=json.dumps(json.loads(result.stdout), indent=2))]
    except json.JSONDecodeError:
        return [TextContent(type="text", text=result.stdout.strip() or f"HTTP {result.returncode}")]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
