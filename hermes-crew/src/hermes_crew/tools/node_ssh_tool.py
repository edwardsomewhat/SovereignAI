"""
Node SSH Tool — Execute commands on any SovereignAI node.

Used by the Infra agent to check node health, disk space,
GPU status, Docker containers, and run diagnostics.
"""
import os
import logging
from datetime import datetime
from crewai.tools import tool

try:
    import paramiko
except ImportError:
    paramiko = None

log_dir = "/home/fated/knowledge/logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "node_commands.log"),
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)

KNOWN_NODES = {
    "sovereign": {"host": "100.124.230.56", "user": "fated"},
    "hq-ai":     {"host": "100.84.92.74",  "user": "fated"},
    "omega":     {"host": "100.84.226.78", "user": "fated"},
    "conchai":   {"host": "100.69.153.16", "user": "fated"},
    "theconch":  {"host": "100.64.45.87",  "user": "edward"},
    "charlotte": {"host": "100.70.223.108","user": "fated"},
    "cs":        {"host": "100.71.6.98",   "user": "fated"},
    "csweb":     {"host": "100.71.6.98",   "user": "fated"},
    "nano":      {"host": "100.81.229.44", "user": "fated"},
}

BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
    ":(){ :|:& };:", "> /dev/sda", "chmod -R 777 /",
    "shutdown", "reboot", "init 0", "init 6",
]


def _is_blocked(command: str) -> bool:
    cmd_lower = command.strip().lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return True
    return False


@tool("Run Command on Node")
def run_node_command(node: str, command: str) -> str:
    """
    Execute a shell command on any SovereignAI node via SSH.
    Use this to check node health, disk space, GPU status,
    running services, or run diagnostics.

    Args:
        node: Node name. One of: sovereign, hq-ai, omega, conchai,
              theconch, charlotte, cs, csweb, nano
        command: The shell command to execute on the node.
    """
    if paramiko is None:
        return "❌ paramiko not installed. Run: pip install paramiko"

    if _is_blocked(command):
        logging.warning(f"BLOCKED on {node}: {command}")
        return f"❌ Command blocked by security policy: {command}"

    if node not in KNOWN_NODES:
        return f"❌ Unknown node '{node}'. Known nodes: {', '.join(KNOWN_NODES.keys())}"

    node_info = KNOWN_NODES[node]
    host = node_info["host"]
    user = node_info["user"]

    logging.info(f"EXEC on {node} ({host}): {command}")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Try key-based auth, fall back to password from env
        key_path = os.path.expanduser(f"~/.ssh/id_rsa")
        connect_kwargs = {
            "hostname": host,
            "username": user,
            "timeout": 15,
        }

        if os.path.exists(key_path):
            connect_kwargs["key_filename"] = key_path
        else:
            pw = os.getenv(f"NODE_PASSWORD_{node.upper().replace('-','_')}")
            if pw:
                connect_kwargs["password"] = pw

        client.connect(**connect_kwargs)
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        exit_code = stdout.channel.recv_exit_status()

        output = stdout.read().decode("utf-8", errors="replace")
        errors = stderr.read().decode("utf-8", errors="replace")
        client.close()

        result_parts = [f"📡 {node} ({host}):"]
        if output:
            result_parts.append(f"📤 Output:\n{output.rstrip()}")
        if errors:
            result_parts.append(f"⚠️ Stderr:\n{errors.rstrip()}")
        result_parts.append(f"Exit code: {exit_code}")

        result = "\n".join(result_parts)
        logging.info(f"RESULT [{node}] (exit {exit_code}): {output[:200]}")
        return result

    except paramiko.AuthenticationException:
        return f"❌ SSH auth failed for {node} ({host}). Check SSH key or password."
    except paramiko.SSHException as e:
        return f"❌ SSH error on {node}: {e}"
    except Exception as e:
        return f"❌ Connection error to {node} ({host}): {e}"


@tool("Health Check All Nodes")
def health_check_all() -> str:
    """
    Run a quick health check on ALL 8 SovereignAI nodes.
    Checks: online status, disk usage, memory, and Docker containers.
    No arguments needed.
    """
    results = []
    checks = {
        "disk": "df -h / | tail -1 | awk '{print $5}'",
        "memory": "free -h | grep Mem | awk '{print $3\"/\"$2}'",
        "uptime": "uptime -p",
        "docker": "docker ps --format '{{.Names}}' 2>/dev/null | wc -l",
    }

    for node_name, node_info in KNOWN_NODES.items():
        host = node_info["host"]
        user = node_info["user"]

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key_path = os.path.expanduser("~/.ssh/id_rsa")
            connect_kwargs = {"hostname": host, "username": user, "timeout": 10}
            if os.path.exists(key_path):
                connect_kwargs["key_filename"] = key_path

            client.connect(**connect_kwargs)

            node_status = f"🟢 {node_name} ({host})"
            for check_name, check_cmd in checks.items():
                stdin, stdout, stderr = client.exec_command(check_cmd, timeout=10)
                val = stdout.read().decode("utf-8", errors="replace").strip()
                node_status += f"\n   {check_name}: {val or 'N/A'}"

            client.close()
            results.append(node_status)

        except Exception as e:
            results.append(f"🔴 {node_name} ({host}): OFFLINE — {e}")

    return "\n\n".join(results)
