#!/usr/bin/env python3
"""Monitor a running Sovereign training pipeline background process.
Tracks directory file counts and detects process exit.

WARNING: execute_code has a 300s hard timeout. This script's default
max_wait of 1800s will ALWAYS time out when run via execute_code.
For grade stages taking >5 min, use one of these instead:
  1. File-count monitoring via terminal() every 30-60s (Option B in skill)
  2. Log-file redirect + tail polling (Option A in skill)
  3. Run this script directly from terminal in background mode
     (not via execute_code), e.g.:
     terminal("python scripts/monitor-pipeline.py <PID>", background=True, timeout=1800)

For fast runs (<5 min) where execute_code is sufficient, reduce max_wait.
"""

import os
import time
from pathlib import Path


def monitor(pid: int, max_wait: int = 1800, interval: int = 30):
    """Poll file counts and process liveness until pipeline exits.

    Args:
        pid: Background process PID to monitor.
        max_wait: Maximum seconds to wait (default 30 min).
        interval: Seconds between polls (default 30).
    """
    training_dir = Path.home() / ".hermes" / "training_data"
    raw_dir = training_dir / "raw"
    processed_dir = training_dir / "processed"
    curated_dir = training_dir / "curated"

    def counts():
        return (
            len(list(raw_dir.glob("*.md"))),
            len(list(processed_dir.glob("*.txt"))),
            len(list(curated_dir.glob("*.txt"))),
        )

    def alive():
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    start = time.time()
    last_raw, last_proc, last_cur = counts()
    print(f"Initial: raw={last_raw} processed={last_proc} curated={last_cur}")
    print("Monitoring...")

    while time.time() - start < max_wait:
        time.sleep(interval)
        r, p, c = counts()
        is_alive = alive()
        changed = (r != last_raw or p != last_proc or c != last_cur)
        elapsed = int(time.time() - start)

        if changed or is_alive:
            tag = "(running)" if is_alive else "(DONE!)"
            print(f"[{elapsed}s] raw={r} proc={p} cur={c} {tag}")
            last_raw, last_proc, last_cur = r, p, c

        if not is_alive:
            break

    r, p, c = counts()
    print(f"\nFinal: raw={r} processed={p} curated={c}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python monitor-pipeline.py <PID> [max_wait_seconds] [interval_seconds]")
        sys.exit(1)
    pid = int(sys.argv[1])
    max_wait = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    monitor(pid, max_wait, interval)
