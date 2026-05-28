#!/bin/bash
# Network Scout — node discovery script
# Scans all SovereignAI nodes and returns structured data
# Usage: bash scan-network.sh [--quick]

QUICK=${1:-false}

NODES=(
  "conchai:100.69.153.16"
  "hq-ai:100.84.92.74"
  "omega:100.84.226.78"
  "csweb:100.71.6.98"
  "Fat-Eds-Eyes:100.81.229.44"
  "cs:100.79.117.119"
  "charlotte:100.70.223.108"
)

scan_node() {
  local name=$1
  local ip=$2
  
  echo "=== $name ($ip) ==="
  ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no fated@$ip '
    echo "HOST: $(hostname)"
    echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d \"\\\"\")"
    echo "UPTIME: $(uptime -p)"
    echo "CPU: $(nproc) cores"
    echo "MEM: $(free -h | grep Mem | tr -s " " | cut -d" " -f3)/$(free -h | grep Mem | tr -s " " | cut -d" " -f2)"
    echo "DISK: $(df -h / | tail -1 | tr -s " " | cut -d" " -f3)/$(df -h / | tail -1 | tr -s " " | cut -d" " -f2) ($(df -h / | tail -1 | tr -s " " | cut -d" " -f5))"
    echo "GPU: $(nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo none)"
    echo "---SERVICES---"
    curl -s -o /dev/null -w "ComfyUI:8188=%{http_code}\n" http://localhost:8188/system_stats 2>/dev/null || echo "ComfyUI:8188=down"
    curl -s -o /dev/null -w "Ollama:11434=%{http_code}\n" http://localhost:11434 2>/dev/null || echo "Ollama:11434=down"
    curl -s -o /dev/null -w "vLLM:8000=%{http_code}\n" http://localhost:8000/health 2>/dev/null || echo "vLLM:8000=down"
    echo "---DOCKER---"
    docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "no docker"
  ' 2>/dev/null
  echo ""
}

echo "# Network Scout Scan — $(date -u +'%Y-%m-%d %H:%M UTC')"
echo ""

for node_info in "${NODES[@]}"; do
  name="${node_info%%:*}"
  ip="${node_info##*:}"
  scan_node "$name" "$ip"
done
