# Jetson Vision Pipeline — Error Transcripts & Fixes

## Error: `operator torchvision::nms does not exist`

```
RuntimeError: operator torchvision::nms does not exist
```

**Cause**: PyPI torchvision wheel compiled against a different torch ABI than the NVIDIA Jetson torch wheel. The `torchvision::nms` C++ operator is registered during import and fails when the linked torch libraries don't match.

**Fix**: DO NOT install torchvision from PyPI. Build from source (v0.19.1) with setuptools==69.5.1 against the installed NVIDIA torch.

---

## Error: `canonicalize_version() got an unexpected keyword argument 'strip_trailing_zero'`

```
TypeError: canonicalize_version() got an unexpected keyword argument 'strip_trailing_zero'
```

**Cause**: setuptools 70+ incompatible with the torchvision build system on JetPack 6.

**Fix**: Pin `setuptools==69.5.1`. Do not use 68.x (too old) or 70+.

---

## Error: `AttributeError: 'Florence2LanguageConfig' object has no attribute 'forced_bos_token_id'`

```
AttributeError: 'Florence2LanguageConfig' object has no attribute 'forced_bos_token_id'
```

**Cause**: transformers 5.0 changed the config initialization order. Florence 2's custom `configuration_florence2.py` accesses `forced_bos_token_id` before the parent `__init__` sets it.

**Fix**: Downgrade transformers to 4.48.3 and clear HF cache:
```bash
pip3 install --user transformers==4.48.3
rm -rf ~/.cache/huggingface/modules/transformers_modules/microsoft/Florence*
```

---

## Error: `ImportError: This modeling file requires flash_attn`

```
ImportError: This modeling file requires the following packages that were not found in your environment: flash_attn
```

**Cause**: transformers 4.44.x has a rigid `check_imports` function that scans for ALL imports in the model file, even those inside conditional `if is_flash_attn_2_available()` blocks.

**Fix**: Use transformers 4.48.3 — it does not have this overly aggressive check.

---

## Error: `ModuleNotFoundError: No module named 'torch._C._distributed_c10d'`

```
ModuleNotFoundError: No module named 'torch._C._distributed_c10d'; 'torch._C' is not a package
```

**Cause**: NVIDIA Jetson torch wheel ships `torch/distributed/` directory without compiled `torch._C._distributed_c10d`. The FSDP import chain (`torch.distributed.fsdp` → `_flat_param.py` → `fake_pg.py` → `_distributed_c10d`) fails.

**Fix**: Monkey-patch `is_fsdp_managed_module` and `is_deepspeed_zero3_enabled` BEFORE any transformers import (see SKILL.md Step 5).

---

## Error: `AttributeError: 'Florence2ForConditionalGeneration' object has no attribute '_supports_sdpa'`

```
AttributeError: 'Florence2ForConditionalGeneration' object has no attribute '_supports_sdpa'
```

**Cause**: Older transformers (4.57.6) tried to check `_supports_sdpa` which Florence 2's custom model code doesn't define.

**Fix**: Pin to transformers 4.48.3.

---

## Error: `RevisionNotFoundError: 404 Client Error`

```
RevisionNotFoundError: e5f68a7 is not a valid git identifier
```

**Cause**: Attempting to pin to a specific Florence 2 revision that doesn't exist.

**Fix**: Use the default `main` branch. The `revision` parameter is not needed with transformers 4.48.3.

---

## Domain Resolution Table

These were tested FROM the Jetson device (nano-box / Fat-Eds-Eyes):

| Domain | DNS Result | HTTP Result |
|--------|-----------|-------------|
| `pypi.jetson-ai-lab.io` | Resolves | 200 OK |
| `pypi.jetson-ai-lab.dev` | NXDOMAIN | N/A |
| `jetson.webredirect.org` | 162.216.242.206 | 302 → .dev (dead) |
| `download.pytorch.org` | Resolves | 200 OK (CPU wheels only) |
| `developer.download.nvidia.com` | Resolves (Akamai) | 307 → login wall for directory listings |

---

## NVIDIA Torch Wheel URL Construction

For JetPack 6.x, the CUDA torch wheel follows this pattern:
```
https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl
```

- `jp/v61` = JetPack 6.1 (works with 6.0 and 6.2)
- `cp310` = Python 3.10
- `nv24.08` = NVIDIA build from August 2024

To find newer wheels, check the [NVIDIA PyTorch for Jetson docs](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html) and the [compatibility matrix](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform-release-notes/pytorch-jetson-rel.html).
