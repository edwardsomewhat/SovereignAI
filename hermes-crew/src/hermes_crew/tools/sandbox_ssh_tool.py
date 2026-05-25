"""
Sandbox SSH Tool — Execute commands on the Omega VM
Target: fated@100.84.226.78 (Omega sandbox)

Security guardrails:
  - Only connects to the configured OMEGA_HOST
  - Destructive commands are blocked by a denylist
  - All commands are logged
  - 30-second timeout per command
"""
import os
import logging
from datetime import datetime
from crewai.tools import tool

try:
    import paramiko
except ImportError:
    paramiko = None

# Set up logging for sandbox commands
log_dir = "/home/fated/knowledge/logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "sandbox_commands.log"),
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)

# Commands that should never be executed
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",
    "> /dev/sda",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "init 0",
    "init 6",
]


def _is_blocked(command: str) -> bool:
    """Check if a command matches any blocked pattern."""
    cmd_lower = command.strip().lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return True
    return False


@tool("Execute Sandbox Command")
def execute_sandbox_command(command: str) -> str:
    """
    Execute a shell command on the Omega sandbox VM via SSH.
    This is a safe, isolated environment for testing code and running experiments.
    Destructive commands (rm -rf /, mkfs, etc.) are blocked.

    Args:
        command: The shell command to execute on the sandbox VM.
    """
    if paramiko is None:
        return "❌ paramiko is not installed. Run: pip install paramiko"

    if _is_blocked(command):
        logging.warning(f"BLOCKED: {command}")
        return f"❌ Command blocked by security policy: {command}"

    host = os.getenv("OMEGA_HOST", "100.84.226.78")
    user = os.getenv("OMEGA_USER", "fated")
    key_path = os.getenv("OMEGA_SSH_KEY", "/home/fated/.ssh/omega_sandbox")
    password = os.getenv("OMEGA_PASSWORD")

    logging.info(f"EXEC on {host}: {command}")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Prefer key-based auth, fall back to password
        connect_kwargs = {
            "hostname": host,
            "username": user,
            "timeout": 10,
        }

        if os.path.exists(key_path):
            connect_kwargs["key_filename"] = key_path
        elif password:
            connect_kwargs["password"] = password
        else:
            return "❌ No SSH key or password configured for Omega VM."

        client.connect(**connect_kwargs)

        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        exit_code = stdout.channel.recv_exit_status()

        output = stdout.read().decode("utf-8", errors="replace")
        errors = stderr.read().decode("utf-8", errors="replace")

        client.close()

        result_parts = []
        if output:
            result_parts.append(f"📤 Output:\n{output}")
        if errors:
            result_parts.append(f"⚠️ Stderr:\n{errors}")
        result_parts.append(f"Exit code: {exit_code}")

        result = "\n".join(result_parts)
        logging.info(f"RESULT (exit {exit_code}): {output[:200]}")

        return result

    except paramiko.AuthenticationException:
        return "❌ SSH authentication failed. Check credentials or SSH key."
    except paramiko.SSHException as e:
        return f"❌ SSH error: {e}"
    except Exception as e:
        return f"❌ Connection error: {e}"
