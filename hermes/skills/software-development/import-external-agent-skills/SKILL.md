---
name: import-external-agent-skills
description: Import third-party agent skills and rules (Claude Code SKILL.md, AGENTS.md, Cursor rules) into Hermes Agent. Use when user has a repo of skills or rules they want integrated.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, import, conversion, third-party, claude-code, agents-md]
    related_skills: [hermes-agent-skill-authoring, github-auth]
---

# Import External Agent Skills & Rules

## Overview

Third-party agent configuration repos are increasingly common — Claude Code skill packs, AGENTS.md rule collections, and Cursor rules. These are plain markdown files with YAML frontmatter, which means they're largely compatible with Hermes Agent's skill format already.

This skill covers importing two common formats:
- **SKILL.md repos** (Claude Code skills) — organized in skill directories with YAML frontmatter, nearly identical to Hermes Agent skill format
- **AGENTS.md repos** (rule collections from programming books) — plain markdown rule files, organized by book/subject, released in full/mini/nano variants

## Detection

Before importing, determine what you're working with:

```bash
# Check structure
ls <repo>/
ls <repo>/skills/ 2>/dev/null
ls <repo>/<book-name>/ 2>/dev/null
```

Signals:
- YAML frontmatter (`---\nname: ...\ndescription: ...\n---`) → SKILL.md format, direct import
- Bucket folders like `engineering/`, `productivity/`, `misc/` → mattpocock/skills style
- Book directories with `full`, `mini`, `nano` variants → agent-rules-books style
- Plain markdown with `AGENTS.md` style headings → rule-set format, needs conversion

## Workflow: Importing SKILL.md Skills (mattpocock/skills style)

These have YAML frontmatter with `name` and `description` — already Hermes-compatible.

### Step 1: Clone the repo

```bash
git clone https://github.com/<owner>/<repo>.git /path/to/clone
```

### Step 2: Pick skills to import

Look at each skill's SKILL.md. Check:
- Is the content useful for Hermes Agent? (general engineering wisdom vs Claude Code-specific toolage)
- Does the description and trigger make sense for your work?
- Does it reference Claude Code-specific features (slash commands, `/setup-*` commands)?

### Step3: Copy to Hermes skills dir

```bash
# Copy individual skill
cp -r /path/to/clone/skills/<bucket>/<skill-name> ~/.hermes/skills/<category>/
```

### Step 4: Verify

```bash
# Check frontmatter is valid
head -5 ~/.hermes/skills/<category>/<skill-name>/SKILL.md
# Should start with ---, have name: and description:~
```

**Pitfalls:**
- Some Claude Code skills reference `.claude-plugin/plugin.json` or `/setup-*` commands — those don't exist in Hermes Agent. Either skip those skills or strip the references.
- Claude Code skills may reference `scripts/*.js` by relative path. For Hermes, `skill_manage(action='write_file')` only allows `scripts/` under target, so JS scripts can coexist but the agent needs to know they exist.

## Workflow: Import AGENTS.md Rule Sets (agent-rules-books style)

These are plain markdown files organized by book, with three size variants per book.

### Step 1: Clone the repo

```bash
git clone https://github.com/<owner>/<repo>.git /path/to/clone
```

### Step 2: Choose variant

Each book has three sizes:
- **full** — canonical version, longest
- **mini** — recommended for most tasks (46-65 lines)
- **nano** — fallback for tight context (32-44 lines)

Prefer **mini** for skill use — it's the Goldilocks size.

### Step 3: Create a Hermes Agent skill

These rules don't have YAML frontmatter, so you create a wrapper SKILL.md:

**Option A: Inline rules (for mini/nano)**

Create `~/.hermes/skills/software-development/<book-name>/SKILL.md`:

```markdown
---
name: <book-name>
description: Use when writing or reviewing code and want <book> design principles applied.
version: 1.0.0
author: Imported from mattpocock/agent-rules-books
license: MIT
metadata:
  hermes:
    tags: [rules, code-quality, <book-tag>]
    related_skills: []
---

# <Book Title> Rules

<Full content of the mini rule file>
```

**Option B: Reference file (for full rules)**

Create a SKILL.md that must reference a supporting file:

```markdown
---
name: <book-name>
description: Use when ...
version: 1.0.0
# ...
---

# <Book Title> Rules

See [references/book-rules.md](references/book-rules.md) for the full rule set.
```

Then add the rules as a reference file:
```bash
skill_manage(action='write_file', name='<book-name>', file_path='references/book-rules.md', file_content='<content>')
```

### Step 4: Verify

```bash
skill_view(name='<book-name>')
# Should print the skill content with rules visible
```

**Pitfall:** Don't import `full` as the inline content — some exceed the 100K char SKILL.md limit. Use it in `references/` instead.

## Which Books to Import

From the agent-rules-books repo, prioritize based on your work:

| Book | Best for |
|------|----------|
| Clean Code | Everyday code quality, readability, naming |
| A Philosophy of Software Design | API design, module boundaries, complexity |
| Refactoring | Safe code improvement, smell detection |
| Working Effectively with Legacy Code | Legacy codebases, adding tests to untested code |
| The Pragmatic Programmer | General engineering discipline |
| Clean Architecture | System architecture, dependency injection |
| Designing Data-Intensive Applications | Database/reliability/data pipeline work |
| Domain-Driven Design | Domain modeling, bounded contexts |
| Release It! | Production reliability, resilience patterns |

## Common Pitfalls

1. **Expecting Claude Code-specific features to work.** Features like `.claude-plugin/plugin.json`, slash commands, `/setup-*`, or `scripts/` referencing JS utilities with Claude-specific env vars will not work in Hermes. Review skills for these before importing and either adapt or skip them.

2. **Frontmatter mismatch.** Some external SKILL.md files have more/less frontmatter than Hermes requires. Hermes only needs `name` and `description`. Add `version`, `author`, `license`, and `metadata.hermes` to make the skill look like a peer.

3. **Assuming bucket organization maps cleanly.** `engineering/`, `productivity/`, `misc/` in Claude Code repos may not map 1:1 to Hermes categories. Place skills in the closest Hermes category (`software-development/`, `productivity/`, etc.) or a catch-all.

4. **Over-importing.** Not every external skill is useful. Import selectively — Vetting each SKILL.md's triggers and content before copying.

5. **Token regeneration on fine-grained PATs.** If the user needs to edit token permissions to clone private repos or push, editing the token on GitHub.com regenerates it. Have them send the new value.

## Verification Checklist

- [ ] SKILL.md has valid YAML frontmatter (`name`, `description`)
- [ ] No broken references to Claude Code-specific features
- [ ] Skill content fits within the 100K char limit (move oversized content to `references/`)
- [ ] `skill_view()` loads the skill without errors
- [ ] Skill is discoverable via `skills_list()`