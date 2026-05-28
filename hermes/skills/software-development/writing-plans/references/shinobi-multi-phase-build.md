# Multi-Phase Build Pattern — Shinobi Example

## Pattern

When building a large multi-component system, break it into independent phases,
each a sibling Python package under a common project root. Each phase's output
is the next phase's input — a pipeline, not a monolith.

```
~/.hermes/<project>/
├── packager/          # Phase 1 — produces payloads (static configs)
├── spawner/           # Phase 2 — consumes payloads, produces results
├── vanish/            # Phase 3 — consumes results, produces intel + archive
├── processor/         # Phase 4 — consumes intel, produces memory/graphify/session
└── tests/             # All phases share one test directory
```

## Why This Works

- **No circular dependencies.** Each phase depends on prior phases' output
  format (dataclasses), not their implementation. Phase 3 imports Phase 2's
  `MissionResult` but Phase 2 never imports Phase 3.
- **Test independently.** Each phase's tests mock upstream — no need for real
  model calls. 64 tests ran in 0.58s.
- **Incremental delivery.** Each phase is a working system. Phase 1 alone
  produces deployable payloads. Phase 1+2 executes them. Phase 1+2+3 completes
  the lifecycle.

## Pipeline Flow

```
Task spec → Packager → payload/ → Dispatcher → sub-agents → MissionResult
                                                        ↓
                                  Vanish ← intel.json + archive + purge
                                     ↓
                                  Processor → memory entries + graphify cmds + session summary
```

## Pytest Config Pattern

Each package gets its own `pyproject.toml` with pytest config pointing to the
shared `../tests/` directory from the package's perspective:

```toml
[tool.pytest.ini_options]
testpaths = ["../tests"]
pythonpath = [".."]   # parent dir so `import <pkg>` works
```

## Phase Handoff Pattern

Each phase's output format is a dataclass or structured dict that the next phase
imports. No phase calls another phase's runtime functions — they only import
data structures:

```python
# Phase 2 imports Phase 1's output (from packager.generator)
# Phase 3 imports Phase 2's output (from spawner.dispatcher, spawner.packet)
# Phase 4 imports Phase 3's output (intel packet dict)
```

## Verification After Each Phase

```bash
cd <any_package_dir>
python3 -m pytest ../tests/ -v    # Test entire project from any package
```

Total test count after 4 phases: 64 tests, 0.58s runtime.
