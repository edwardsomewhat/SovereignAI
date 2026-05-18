# Importing External Agent Skills into Hermes Agent

This guide covers importing skills from **Claude Code**, **Codex**, **Cursor**, or any **AGENTS.md**-based skill repository into Hermes Agent's `~/.hermes/skills/` system.

## Compatible Formats

| Source Format | Compatibility | Action Needed |
|---|---|---|
| **SKILL.md with YAML frontmatter** (name, description) | ✅ Direct import | Copy SKILL.md + linked files as-is |
| **AGENTS.md rule files** (markdown lists, no frontmatter) | ⚠️ Needs conversion | Wrap in proper YAML frontmatter |
| **CLAUDE.md rules** (markdown sections) | ⚠️ Needs conversion | Same as AGENTS.md treatment |
| **Cursor rules (.mdc)** | ⚠️ Needs conversion | Strip .mdc metadata, add Hermes frontmatter |
| **JSON/YAML plugin manifests** (e.g. plugin.json) | ❌ Not importable | Extract skill definitions manually |

## Import Workflow

### 1. Survey the External Repo

```bash
# Clone the repo first
git clone <repo-url> ~/repos/<name>

# Understand the structure
find ~/repos/<name> -name "SKILL.md" | sort
# OR for AGENTS.md repos:
ls -R ~/repos/<name>/
```

### 2. Check Frontmatter Compatibility

Hermes Agent requires this frontmatter (minimal):

```yaml
---
name: skill-name          # lowercase, hyphens, ≤64 chars
description: Use when ... # ≤1024 chars, starts with "Use when"
---
```

Matt Pocock's skills already have this. Other repos may not — you'll need to:

- Read each source file
- Extract or infer name/description from content
- Construct proper frontmatter
- Wrap content as the SKILL.md body

### 3. Copy or Convert

**Direct copy (compatible SKILL.md):**
```bash
cp -r ~/repos/<name>/skills/<category>/<skill> ~/.hermes/skills/<category>/<skill>/
```

**Conversion (AGENTS.md → SKILL.md):**
```python
import yaml
skill_md = f"""---
name: {skill_name}
description: Use when {trigger_context}
version: 1.0.0
author: imported from <source>
license: MIT
metadata:
  hermes:
    tags: [relevant, tags]
    related_skills: []
---

# []
---

# {title}

{content_from_source}
"""
```

### 4. Handle Linked Files

External skills often come with supporting files. Place them in the right subdirectory inside `~/.hermes/skills/<category>/<skill>/`:

| External file type | Hermes target dir |
|---|---|
| Reference docs (.md, .txt) | `references/` |
| Scripts (.sh, .py, .ts, .js) | `scripts/` |
| Boilerplate/configs | `templates/` |

### 5. Verify

```bash
# Check frontmatter is valid
head -6 ~/.hermes/skills/<category>/<skill>/SKILL.md
# Should start with --- and have name: + description:

# Check file count
find ~/.hermes/skills/ -name "SKILL.md" | wc -l
```

## Book AGENTS.md → Skill Conversion Pattern

The `agent-rules-books` repo stores each book's rules in three variants: `full`, `mini` (recommended), and `nano`. When converting:

1. **Use the mini version** (30-65 lines) — it's concise enough for agent context and has the best signal-to-noise ratio
2. **Save the full version as a reference** in `references/` for when the agent needs deeper detail
3. **Set the skill name** to the book's slug (e.g. `clean-code`, `ddia`, `refactoring`)
4. **Set description** to something like: `"Use when building or reviewing code. Apply design principles from '{Book Title}'. Load to enforce architectural and code quality rules inspired by the book."`
5. **Strip any existing frontmatter** from the source before wrapping — the source may have its own YAML block that doesn't match Hermes format

## Common Pitfalls

1. **Claude Code-specific commands in skill body.** Skills that reference `/command` slash-commands, `claude` tool calls, or `@workspace` don't exist in Hermes. Strip or adapt these references on import.
2. **Missing frontmatter.** Hermes enforces `name` + `description` in YAML frontmatter. Without it, `skill_view()` will not load the skill properly despite the file existing on disk.
3. **Overly specific descriptions.** External skills often have no description or a generic one. Always set `description` starting with `"Use when ..."` so the trigger-based skill selector can match.
4. **File structure overlaps.** The mattpocock/skills repo organizes by bucket (engineering/, productivity/, misc/). Hermes Agent already has its own category system — map buckets to the closest Hermes category rather than blindly copying.