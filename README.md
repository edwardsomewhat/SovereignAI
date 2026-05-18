# SovereignAI
### A hardware/software stack protocol for sovereign self-hosted infrastructure.

This repo is the blueprint for a reproducible Hermes Agent node — part of a larger vision to put 90% of the datacenter in your own basement.

## Contents

```
├── hermes/
│   ├── config.yaml      # Hermes Agent configuration
│   ├── SOUL.md           # Agent persona / personality
│   └── skills/           # 133 agent skills (engineering, productivity, book rules)
├── systemd/
│   ├── hermes-dashboard.service  # Dashboard service definition
│   └── firecrawl.service         # Web scraping service
├── setup.sh             # Bootstrap script for fresh machines
└── README.md
```

## Quick Start on a New Machine

```bash
# Clone this repo
git clone https://github.com/edwardsomewhat/SovereignAI.git
cd SovereignAI

# Run the setup
./setup.sh

# Configure secrets
# Add your GITHUB_TOKEN and API keys to ~/.hermes/.env
```

## Skills Included

**Engineering** — TDD, diagnose, prototype, zoom-out, codebase architecture, triage, PRD writing, issue tracking, grill-with-docs

**Productivity** — handoff, write-a-skill, grill-me, caveman (ultra-compressed mode)

**Misc** — git guardrails, pre-commit setup, scaffold-exercises, migrate-to-shoehorn

**Book Rule Sets** — Rules distilled from 14 classic software engineering books:
- Clean Code, Clean Architecture, Domain-Driven Design (x3), Refactoring (x2)
- Designing Data-Intensive Applications, A Philosophy of Software Design
- Working Effectively with Legacy Code, The Pragmatic Programmer
- Code Complete, Release It!, Patterns of Enterprise Application Architecture

## Node Requirements

- Linux (Ubuntu 24.04+ recommended)
- Hermes Agent (pip install hermes-agent)
- Tailscale (for secure mesh networking between nodes)
- Python 3.12+

## Intent

> *"I don't want to play ball, I want to destroy the playing field."*

This stack exists to remove the pretext for corporate infrastructure dependency. Each node is a self-contained sovereign compute unit — no cloud vendor lock-in, no tax-subsidized surveillance, no reliance on entities that treat us with disdain.