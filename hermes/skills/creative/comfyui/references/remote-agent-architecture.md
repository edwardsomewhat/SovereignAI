# Remote Agent Architecture

Pattern for running an autonomous agent on one machine that controls ComfyUI
on a separate GPU node. The agent survives GPU crashes/OOMs because it lives
on a different host.

## Topology

```
┌──────────────────────┐     Tailscale      ┌──────────────────────┐
│   Orchestrator Node  │◄──────────────────►│    GPU/ComfyUI Node  │
│   (sovereign)        │   100.69.x.x:8188  │    (ConchAI)         │
│                      │                    │                      │
│  Art Director Agent  │──POST /api/prompt─►│  ComfyUI :8188       │
│  comfyui skill       │                    │  RTX 3090            │
│  scripts/*.py        │◄──JSON outputs────│  systemd service     │
│                      │                    │                      │
│  Browser ────────────┼───────────────────►│  File Browser :8190  │
│  (output access)     │   any tailnet node │  (outputs + inputs)  │
└──────────────────────┘                    └──────────────────────┘
```

## Key Design Decisions

1. **Agent runs on orchestrator, not GPU node.** If ComfyUI OOMs or crashes
   on the GPU node, the agent on the orchestrator simply gets a connection
   error and retries. The GPU node's systemd service auto-restarts ComfyUI.

2. **Tailscale for connectivity.** All traffic stays on the tailnet — no
   exposed ports to the internet. The orchestrator reaches ComfyUI at the
   GPU node's Tailscale IP (e.g., `100.69.153.16:8188`).

3. **COMFY_HOST env var** on the orchestrator node points at the GPU node.
   Set in `~/.bashrc`:
   ```bash
   export COMFY_HOST='http://100.69.153.16:8188'
   ```

4. **`_common.py` patch** makes the scripts read `COMFY_HOST`:
   ```python
   DEFAULT_LOCAL_HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
   ```
   This means `run_workflow.py`, `health_check.py`, etc. auto-target the
   remote GPU node without needing `--host` on every call.

## Output Access

- **File Browser** on the GPU node (port 8190): web-based file manager
  accessible from any tailnet device. Supports upload (for reference images)
  and download (for generated outputs). Works on mobile.
- **Direct fetch via API:** the scripts download outputs to the orchestrator's
  local filesystem after each run.
- **SCP/SFTP** for bulk transfers between nodes.

## Verification

From the orchestrator node:
```bash
curl -s http://100.69.153.16:8188/system_stats | python3 -m json.tool
```

From the GPU node, test orchestrator connectivity:
```bash
ssh orchestrator "curl -s http://100.69.153.16:8188/system_stats"
```

Full health check from orchestrator:
```bash
cd ~/.hermes/skills/creative/comfyui
COMFY_HOST=http://100.69.153.16:8188 python3 scripts/health_check.py
```
