# Python Project Scaffolding — Pitfalls & Patterns

## Pytest config in pyproject.toml

When building a multi-package Python project under a common root, the
`pyproject.toml` inside each package needs careful path configuration:

```toml
# Inside each package subdirectory (e.g. ~/.hermes/shinobi/packager/pyproject.toml)
[tool.pytest.ini_options]
testpaths = ["../tests"]       # Tests live one level up from the package
pythonpath = [".."]            # Parent dir on PYTHONPATH so `import packagename` works
```

**Why `pythonpath = [".."]` and not `["."]`:** When pytest runs from inside a
package directory, the cwd is the package dir itself. Python's import system
needs the *parent* directory on sys.path so `import packagename` resolves to
`<parent>/packagename/__init__.py`. With `["."]` it looks for
`<cwd>/packagename/__init__.py` which doesn't exist — the cwd IS packagename.

## Imports when cwd is the package directory

When running manually from within a package directory:

```bash
# WRONG — can't find the package
cd ~/.hermes/shinobi/spawner
python3 -c "from spawner.config import load_payload"  # ModuleNotFoundError

# RIGHT — parent dir on PYTHONPATH
cd ~/.hermes/shinobi/spawner
PYTHONPATH=.. python3 -c "from spawner.config import load_payload"  # OK
```

## Verification after scaffolding

After creating `__init__.py` files and a `pyproject.toml`, verify immediately:

```bash
cd <package_dir>
PYTHONPATH=.. python3 -c "import <packagename>; print('OK')"
python3 -m pytest --co | head -3  # verify pytest finds config
```

## CLI script relative imports

When a CLI script uses relative imports (`from .module import ...`) and must be
runnable as both `python3 cli.py` and `python3 -m package.cli`, add an import
guard at the top:

```python
#!/usr/bin/env python3
import sys

# Allow running as both `python -m package.cli` and `python cli.py`
if __name__ == "__main__" and __package__ is None:
    import os
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _parent)
    __package__ = "package"

from .module import thing  # Now works in both modes
```
