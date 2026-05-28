# Multi-Node Hermes Deployment

How to deploy Hermes to a second node, mirror skills, and keep both nodes synchronized via a git repo.

## Deployment

```bash
# On target node
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Configure model to match source node
hermes config set model.default deepseek-v4-pro
hermes config set model.provider deepseek
hermes config set model.base_url https://api.deepseek.com/v1
```

## Skill Sync (rsync)

When SSH key auth is set up between nodes:

```bash
# Push skills from source to target
rsync -avz --delete ~/.hermes/skills/ user@target:~/.hermes/skills/

# Verify
find ~/.hermes/skills -name "SKILL.md" | wc -l  # should match
```

## Repo-Based Sync (SovereignAI pattern)

A git repo serves as the canonical source. Source node runs a sync script that:
1. rsyncs skills, config, SOUL.md to the repo
2. Detects changes (tracked + untracked files)
3. Auto-commits and pushes to GitHub

Target node clones the repo and rsyncs from it.

## SSH Key Auth Between Nodes

Eliminates password prompts and security scanner blocks:

```bash
# Generate key on source if needed
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519

# Add to target's authorized_keys
ssh-copy-id user@target
# Or manually: cat ~/.ssh/id_ed25519.pub >> target:~/.ssh/authorized_keys

# Verify
ssh user@target 'echo works'
```

## GitHub SSH for Both Nodes

Both nodes should have SSH keys registered on GitHub for push/pull access:

```bash
ssh-keygen -t ed25519 -C "user@hostname"
cat ~/.ssh/id_ed25519.pub  # add to github.com/settings/keys
ssh -T git@github.com       # verify
```

## Pitfalls

- `hermes doctor` shows some tools unavailable on fresh install — expected (missing API keys)
- Classic GitHub PATs (`ghp_*`) may fail for HTTPS git operations — use SSH instead
- rsync `--delete` ensures target mirrors source exactly, removing orphaned skills
- Sync script must check for untracked files (`git ls-files --others --exclude-standard`) not just diffs
