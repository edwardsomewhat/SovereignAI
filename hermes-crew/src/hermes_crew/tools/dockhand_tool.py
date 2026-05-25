"""
Dockhand Manager Tool — CrewAI Edition
Ported from the OpenWebUI tool at /home/fated/knowledge/tools/dockhand-manager-tool.py

Interacts with the Dockhand REST API to manage Docker containers
and stacks across the network.
"""
import json
import os
import urllib.request
import urllib.error
from crewai.tools import tool


DOCKHAND_URL = os.getenv("DOCKHAND_URL", "http://100.124.230.56:3001")


def _make_request(endpoint: str, method: str = "GET", data: dict = None, accept_json: bool = False) -> dict:
    """Helper to make HTTP requests to the Dockhand API."""
    url = f"{DOCKHAND_URL}{endpoint}"

    headers = {}
    if accept_json:
        headers["Accept"] = "application/json"

    json_data = None
    if data:
        json_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_body = response.read().decode("utf-8")
            if resp_body:
                return json.loads(resp_body)
            return {"status": "success"}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        return {"error": f"HTTP Error {e.code}: {e.reason}", "details": error_body}
    except urllib.error.URLError as e:
        return {"error": f"URL Error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


@tool("List Dockhand Environments")
def list_environments(query: str = "list") -> str:
    """
    List all available compute nodes (environments) managed by Dockhand.
    Use this FIRST to find the correct env_id before interacting with containers or stacks.
    No input required — just call this tool.
    """
    response = _make_request("/api/environments")
    if isinstance(response, dict) and "error" in response:
        return f"❌ Failed to fetch environments: {response['error']}"

    output = ["✅ Available Compute Nodes:"]
    for env in response:
        env_id = env.get("id", "Unknown")
        name = env.get("name", "Unknown")
        env_type = env.get("connectionType", "Unknown")
        output.append(f"  - ID: {env_id} | Name: {name} | Type: {env_type} | Status: Online")

    return "\n".join(output)


@tool("List Docker Containers")
def list_containers(env_id: int) -> str:
    """
    List all containers running on a specific compute node.

    Args:
        env_id: The integer ID of the environment (compute node).
               Use 'List Dockhand Environments' first to find this.
    """
    response = _make_request(f"/api/containers?env={env_id}")
    if isinstance(response, dict) and "error" in response:
        return f"❌ Failed to list containers: {response['error']}"

    if not response:
        return "ℹ️ No containers found on this node."

    output = [f"✅ Containers on Node {env_id}:"]
    for c in response:
        c_id = c.get("Id", "")[:12]
        names = c.get("Names", ["Unknown"])
        name = names[0].lstrip("/") if names else "Unknown"
        state = c.get("State", "Unknown")
        status = c.get("Status", "Unknown")
        output.append(f"  - [{c_id}] {name} ({state}) - {status}")

    return "\n".join(output)


@tool("Manage Docker Container")
def manage_container(env_id: int, container_id: str, action: str) -> str:
    """
    Perform an action (start, stop, restart) on a specific container.

    Args:
        env_id: The integer ID of the environment (compute node).
        container_id: The full or short ID of the container.
        action: The action to perform — must be 'start', 'stop', or 'restart'.
    """
    valid_actions = ["start", "stop", "restart"]
    if action not in valid_actions:
        return f"❌ Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}"

    response = _make_request(f"/api/containers/{container_id}/{action}?env={env_id}", method="POST")
    if "error" in response:
        return f"❌ Failed to {action} container {container_id}: {response['error']}"

    return f"✅ Successfully issued '{action}' command to container {container_id} on Node {env_id}."


@tool("Deploy Docker Stack")
def deploy_stack(env_id: int, stack_name: str, compose_yaml: str) -> str:
    """
    Deploy a new Docker Compose stack to a specific node.

    Args:
        env_id: The integer ID of the environment (compute node) to deploy to.
        stack_name: A unique name for this stack.
        compose_yaml: The FULL YAML CONTENT of the docker-compose file.
                      Must be complete, valid docker-compose YAML — not a file path.
    """
    data = {
        "name": stack_name,
        "composeFile": str(compose_yaml),
    }

    response = _make_request(f"/api/stacks?env={env_id}", method="POST", data=data, accept_json=True)

    if "error" in response:
        return f"❌ Stack deployment failed:\n{response['error']}\nDetails: {response.get('details', '')}"

    return f"✅ Stack '{stack_name}' deployed successfully to Node {env_id}!\nResponse: {json.dumps(response)}"
