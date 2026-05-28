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

Full health check from orchestrator:\n```bash\ncd ~/.hermes/skills/creative/comfyui\nCOMFY_HOST=http://100.69.153.16:8188 python3 scripts/health_check.py\n```\n\n## Migrating from a Windows ComfyUI Build\n\nWhen the user has a working Windows ComfyUI installation on the same\nmachine (dual-boot), you can cross-pollinate models, custom nodes, and\nworkflows without redownloading everything from HuggingFace:\n\n```bash\n# Mount the Windows NTFS drive read-only\nsudo mkdir -p /mnt/windows_f\nsudo mount -t ntfs -o ro /dev/nvme1n1p2 /mnt/windows_f\n\n# Sync models (--ignore-existing skips already-downloaded files)\nrsync -av --ignore-existing /mnt/windows_f/ComfyUI/models/ /mnt/hermes_data/comfy/models/\n\n# Sync custom nodes\nrsync -av --ignore-existing /mnt/windows_f/ComfyUI/custom_nodes/ /mnt/hermes_data/comfy/custom_nodes/\n\n# Sync workflows\nrsync -av --ignore-existing /mnt/windows_f/ComfyUI/user/ /mnt/hermes_data/comfy/user/\ncp -n /mnt/windows_f/ComfyUI/workflows/*.json /mnt/hermes_data/comfy/user/default/workflows/\n\n# Unmount when done\nsudo umount /mnt/windows_f\n```\n\n**Pitfalls:**\n- The NTFS mount may drop mid-transfer; remount and re-run rsync (--ignore-existing makes it safe).\n- New custom nodes may need `pip install -r requirements.txt` before they load.\n- Some nodes may fail to import due to missing Python packages (`lark`, `decord`, etc.) — install\n  the missing deps and restart ComfyUI.\n- After adding nodes, restart ComfyUI: `systemctl --user restart comfyui.service`.\n- Expect 1-2 import failures from nodes with unmet dependencies; the server still starts.\n- The Windows build's workflow JSONs may reference Windows file paths or model subfolder\n  structures that differ from the Linux layout; be prepared to create symlinks.
