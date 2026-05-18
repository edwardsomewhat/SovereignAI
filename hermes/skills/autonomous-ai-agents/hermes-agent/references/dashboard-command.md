# Hermes Dashboard Command Reference

## Basic Usage

```bash
hermes dashboard [options]
```

## Key Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port PORT` | Port to bind to | 9119 |
| `--host HOST` | Host interface to bind to | 127.0.0.1 (localhost only) |
| `--insecure` | Allow binding to non-localhost addresses (0.0.0.0) | false |
| `--no-open` | Don't automatically open browser | false |
| `--tui` | Enable in-browser Chat tab (embedded hermes --tui) | false |
| `--skip-build` | Skip web UI build step | false |
| `--stop` | Stop all running dashboard processes | N/A |
| `--status` | List running dashboard processes | N/A |

## Network Access Examples

### Localhost-only (default, secure)
```bash
hermes dashboard
# Access at: http://127.0.0.1:9119
```

### Network-accessible (requires --insecure)
```bash
hermes dashboard --insecure --host 0.0.0.0
# Access at: http://<YOUR_IP>:9119
# Replace <YOUR_IP> with your actual IP (LAN, Tailscale, etc.)
```

### Custom port
```bash
hermes dashboard --insecure --port 8080 --host 0.0.0.0
# Access at: http://<YOUR_IP>:8080
```

## Tailscale Specific Usage

To make Hermes dashboard accessible via Tailscale:

```bash
# Get your Tailscale IP
tailscale ip
# Example output: 100.69.153.16

# Start dashboard bound to all interfaces
hermes dashboard --insecure --host 0.0.0.0 --port 9119

# Access from other devices on your tailnet:
# http://100.69.153.16:9119
```

## Process Management

```bash
# Check status
hermes dashboard --status

# Stop all dashboard processes
hermes dashboard --stop

# Restart with new settings
hermes dashboard --stop
hermes dashboard --insecure --host 0.0.0.0 --port 9119
```

## Security Considerations

⚠️ **WARNING**: The `--insecure` flag exposes the dashboard (and potentially your API keys) to the network. 

- Use only on trusted networks (home LAN, Tailscale tailnet with trusted devices)
- Never expose to public internet without additional authentication/proxy
- Consider using a reverse proxy with authentication for production use
- The dashboard does not implement its own authentication - it relies on network-level security

## Troubleshooting

### "Address already in use"
```bash
hermes dashboard --stop
# Then restart
```

### Connection refused/timeouts
1. Verify dashboard is running: `hermes dashboard --status`
2. Check if bound to correct interface: `ss -tlnp | grep :9119`
3. Ensure `--insecure` and `--host 0.0.0.0` are used for network access
4. Check firewall settings

### Local works but network doesn't
- Confirm using `--insecure --host 0.0.0.0` (not just `--insecure`)
- Verify Tailscale/MagicDNS is working: `tailscale ping <target-ip>`
- Check that no intermediate firewall is blocking the port

## Persistent/Background Operation

To run the Hermes dashboard persistently (survives terminal/logout, auto-restarts on failure):

### Using systemd (Linux)

1. Create the service file:
   ```bash
   mkdir -p ~/.config/systemd/user
   cat > ~/.config/systemd/user/hermes-dashboard.service << 'EOF'
[Unit]
Description=Hermes Agent Web Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/home/fated/.local/bin/hermes dashboard --insecure --port 9119 --host 0.0.0.0
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
   ```

2. Enable and start the service:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now hermes-dashboard.service
   ```

3. Check status:
   ```bash
   systemctl --user status hermes-dashboard.service
   ```

### Using terminal background process (temporary)

For non-persistent background operation:

```bash
# Start in background
hermes dashboard --insecure --port 9119 --host 0.0.0.0 &

# Or using nohup for logout persistence
nohup hermes dashboard --insecure --port 9119 --host 0.0.0.0 > dashboard.log 2>&1 &

# To stop later
hermes dashboard --stop
# or kill the background process
```

## Related Commands

- `hermes` - Main CLI (starts chat interface by default)
- `hermes model` - Configure AI model/provider
- `hermes setup` - Interactive setup wizard
- `hermes tools` - Manage enabled toolsets
- `hermes skills` - Skill management