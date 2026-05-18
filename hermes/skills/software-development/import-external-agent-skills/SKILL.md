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
- Is the content useful for Hermes Agent? (general engineering wisdom vs Claude Code-specific toolage?
- Does the description and trigger make sense for your work?
- Does it reference Claude Code-specific features (slash commands, `/setup-*` commands)?

### Step 3: Manual copy to Hermes skills dir

```bash
# Copy individual skill
cp -r /path/to/clone/skills/<bucket>/<skill-name> ~/.hermes/skills/<category>/
```

### Step 4: Batch import via script (for 10+ skills)

When importing many skills at once, use `execute_code` with a Python script that walks the repo tree, handles frontmatter detection, and copies linked files:

```python
import os, re, yaml, shutil
from hermes_tools import terminal

src = os.path.expanduser('~/repos/source-repo/skills')
dest = os.path.expanduser('~/.hermes/skills')
skip_buckets = {'personal', 'in-progress', 'deprecated', 'README'}

for root, dirs, files in os.walk(src):
    if 'SKILL.md' not in files:
        continue
    parts = root.split('/')
    bucket = parts[-2]
    skill_name = parts[-1]
    if bucket in skip_buckets:
        continue

    target_dir = os.path.join(dest, bucket, skill_name)
    os.makedirs(target_dir, exist_ok=True)

    # Copy SKILL.md
    with open(os.path.join(root, 'SKILL.md')) as f:
        content = f.read()
    with open(os.path.join(target_dir, 'SKILL.md'), 'w') as f:
        f.write(content)

    # Auto-detect linked files: .md/.txt → references/, .sh/.py/.js → scripts/
    for item in os.listdir(root):
        if item == 'SKILL.md':
            continue
        item_path = os.path.join(root, item)
        if os.path.isfile(item_path):
            if item.endswith(('.md', '.txt')):
                ref_dir = os.path.join(target_dir, 'references')
                os.makedirs(ref_dir, exist_ok=True)
                shutil.copy2(item_path, os.path.join(ref_dir, item))
            elif item.endswith(('.sh', '.py', '.js', '.ts')):
                scripts_dir = os.path.join(target_dir, 'scripts')
                os.makedirs(scripts_dir, exist_ok=True)
                shutil.copy2(item_path, os.path.join(scripts_dir, item))
```

This preserves external skill reference files so they remain loadable via `skill_view(name=..., file_path='references/...')`.

### Step 5: Verify imported skills

```bash
# Quick frontmatter check on all imported skills
find ~/.hermes/skills/<category> -name "SKILL.md" -exec head -5 {} \; | grep -E "^name:|^description:"

# Spot check a loaded skill"
skill_view(name='<skill-name>')  # Should show content + linked files

**Pitfalls:**
- Some Claude Code skills reference `.claude-plugin/plugin.json` or `/setup-*` commands — those don't exist in Hermes Agent. Either skip those skills or strip the references.
- Claude Code skills may reference `scripts/*.js` by relative path. The scripts still copy and coexist, but the agent needs to discover them via `skill_view()`'s linked_files dict — add a pointer in SKILL.md if the skill depends on them.
- Skills with `metadata.hermes.tags` or `related_skills` referencing Claude-only plugins won't resolve in Hermes — either remove the references or skip the skill fully.
- Bucket folders like `engineering/`, `productivity/`, `misc/` in external repos may not map 1:1 to Hermes categories. Place them in the closest Hermes category or a catch-all.
- Always skip `personal/`, `in-progress/`, and `deprecated/` buckets — they're personal drafts, missing frontmatter, or abandoned.

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

### Step 3: Create a Hermes Agent skill (batch conversion)

These rules don't have YAML frontmatter, so you create a wrapper SKILL.md. For 10+ books, batch-convert with a script:

```python
import os, re, yaml, shutil

src = os.path.expanduser('~/repos/agent-rules-books')
dest = os.path.expanduser('~/.hermes/skills/software-engineering')

for d in sorted(os.listdir(src)):
    book_path = os.path.join(src, d)
    if not os.path.isdir(book_path) or d in ('docs', '_rule-workbench', '.git'):
        continue
    mini_path = os.path.join(book_path, f"{d}.mini.md")
    if not os.path.exists(mini_path):
        continue

    with open(mini_path) as f:
        content = f.read()

    skill_name = d.replace('_', '-')
    book_title = d.replace('-', ' ').title()
    skill_dir = os.path.join(dest, skill_name)
    os.makedirs(skill_dir, exist_ok=True)

    # Strip any existing frontmatter from the mini file
    if content.startswith('---'):
        m = re.match(r'^---\n.*?\n---\n', content, re.DOTALL)
        if m:
            content = content[m.end():]

    desc = f"Use when writing or reviewing code. Apply design principles from '{book_title}'."

    with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
        f.write(f"""---
name: {skill_name}
description: {desc}
version: 1.0.0
author: derived from mattpocock/agent-rules-books
license: MIT
metadata:
  hermes:
    tags: [software-engineering, code-quality, book-rules]
    related_skills: []
---

# {book_title} Rules

{content}
""")

    # Also copy full version as reference
    full_path = os.path.join(book_path, f"{d}.md")
    if os.path.exists(full_path):
        ref_dir = os.path.join(skill_dir, 'references')
        os.makedirs(ref_dir, exist_ok=True)
        shutil.copy2(full_path, os.path.join(ref_dir, f"{d}.full.md"))
```

**Option B: Reference file (for oversized full rules)**

For rule sets too long for inline (some full versions exceed 60K chars), create a SKILL.md that points to a reference file:

```markdown
# <Book Title> Rules

See [references/book-rules.md](references/book-rules.md) for the full rule set.
```

Then add the rules via `skill_manage(action='write_file', name='<skill-name>', file_path='references/book-rules.md', file_content='<content>')`

### Step 4: Verify batch import

```bash
# Count imported skills
find ~/.hermes/skills/software-engineering -name "SKILL.md" | wc -l

# Verify frontmatter on all
find ~/.hermes/skills/software-engineering -name "SKILL.md" | while read f; do
    name=$(head -5 "$f" | grep "^name:" | sed 's/name: //')
    desc=$(head -5 "$f" | grep "^description:" | sed 's/description: //' | head -c 60)
    echo "  $name - $desc..."
done

# Spot check a skill loads
skill_view(name='<skill-name>')
skill_view(name='<skill-name>', file_path='references/<book>.full.md')
```

**Pitfalls:**
- Don't import `full` as the inline content — some exceed the 100K char SKILL.md cap. Use `references/` for oversized content.
- The mini version (46-65 lines) is the Goldilocks size for a skill: actionable but compact. Don't default to full.
- Book dirs may have hyphens or underscores in their names. Convert `_` to `-` for consistent skill names.
- The `.mini.md` files sometimes have existing YAML frontmatter — strip it before wrapping in the skill's own frontmatter.

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

2. **Frontmatter truncation during patching.** When patching a skill's YAML frontmatter that contains colons, backticks, or special characters, the patch tool can corrupt the frontmatter. Always verify with `skill_view()` after patching and fix any truncation immediately.

3. **Assuming bucket organization maps cleanly.** `engineering/`, `productivity/`, `misc/` in Claude Code repos may not map 1:1 to Hermes categories. Place skills in the closest Hermes category (`software-development/`, `productivity/`, etc.) or a catch-all.

4. **Over-importing.** Not every external skill is useful. Import selectively — vetting each SKILL.md's triggers and content before copying. Always skip `personal/`, `in-progress/`, and `deprecated/` buckets.

5. **Token regeneration on fine-grained PATs.** Editing a fine-grained PAT on GitHub.com regenerates its value — old token immediately returns 401. Classic PATs (`ghp_*`) don't have this issue. If the user needs repo creation or full scopes (including `repo`, `workflow`, `admin:org`), recommend switching to a classic PAT rather than upgrading a fine-grained one.

6. **Config secrets leak when committing Hermes setup.** If you're committing `~/.hermes/config.yaml` to a repo for machine replication, check for secrets first. The config typically has empty `api_key: ''` fields (safe), but the `.env` file must NEVER be committed. Use `.gitignore`:

   ```gitignore
   .env
   *.env
   *token*
   *credential*
   ```

7. **Not preserving linked files from external skills.** External skills often bundle reference docs, scripts, or templates alongside their SKILL.md. When batch-copying skills, auto-detect linked files — `.md`/`.txt` go to `references/`, `.sh`/`.py`/`.js`/`.ts` go to `scripts/`, and templates go to `templates/`. The batch script in this skill handles this automatically.

## Verification Checklist

- [ ] SKILL.md has valid YAML frontmatter (`name`, `description`)
- [ ] No broken references to Claude Code-specific features
- [ ] Skill content fits within the 100K char limit (move oversized content to `references/`)
- [ ] `skill_view()` loads the skill without errors
- [ ] Skill is discoverable via `skills_list()`