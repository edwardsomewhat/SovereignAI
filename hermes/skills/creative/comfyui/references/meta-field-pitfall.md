# Workflow _meta Field Pitfall

## Problem

API-format workflows exported from newer ComfyUI versions include `_meta`
keys on each node:

```json
{
  "6": {
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "Prompt"},
    "inputs": {"text": "...", "clip": ["11", 0]}
  }
}
```

ComfyUI 0.21.x's `execution.py:validate_prompt()` chokes on these with:

```
AttributeError: 'str' object has no attribute 'get'
node_title = node_data.get('_meta', {}).get('title')
```

The `_meta` field is a UI hint that `validate_prompt` mishandles when the node
data is parsed as a string during validation. Newer ComfyUI versions (post-0.21)
handle this gracefully.

## Fix

Strip `_meta` from all nodes before submission:

```bash
python3 -c "
import json
path = 'workflow.json'
d = json.load(open(path))
for v in d.values():
    if isinstance(v, dict):
        v.pop('_meta', None)
json.dump(d, open(path, 'w'), indent=2)
"
```

## Detection

If `run_workflow.py` returns HTTP 500 with `AttributeError: 'str' object has
no attribute 'get'` in the server logs (`journalctl --user -u comfyui`), the
workflow likely has `_meta` fields. Run the stripping script above.
