# Qwen Image Edit Pipeline (Canonical)

Discovered after 7 attempts. This is the exact wiring from the lenML demo workflow.

## Required Custom Nodes
- ComfyUI-GGUF (UnetLoaderGGUF)
- comfyui_qwen_image_edit_adv (TextEncodeQwenImageEditAdv, QwenImageEditSimpleScale)
- efficiency-nodes-comfyui (KSampler Efficient, CFGNorm)

## Model Files
- UnetLoaderGGUF: Qwen-Image-Edit-2511-Q6_K.gguf (in models/unet/)
- CLIPLoader: qwen_2.5_vl_7b_fp8_scaled.safetensors, type="qwen_image" (in models/clip/)
- VAELoader: qwen_image_vae.safetensors (in models/vae/)
- LoraLoaderModelOnly: Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors, strength=1 (in models/loras/)

## Workflow Wiring
1. UnetLoaderGGUF → model
2. CLIPLoader (type=qwen_image) → clip
3. VAELoader → vae
4. LoraLoaderModelOnly → model+lora
5. LoadImage → image
6. QwenImageEditSimpleScale (resolution=1024, alignment=32) → scaled image
7. TextEncodeQwenImageEditAdv (image, clip, vae, prompt — NO model input) → CONDITIONING + LATENT
8. TextEncodeQwenImageEdit (image, clip, vae, prompt) → CONDITIONING (negative)
9. CFGNorm (model from lora, strength=1) → normalized model
10. KSampler (Efficient): model from CFGNorm, positive/negative/latent from encoders, optional_vae, seed, steps=4-8, cfg=1-1.5, denoise=1, vae_decode=true → IMAGE
11. SaveImage ← KSampler output slot 5

## Critical Pitfalls
- QwenImageEditSimpleScale is MANDATORY — without it, output becomes 8-bit pixel art
- TextEncodeQwenImageEditAdv does NOT accept a "model" input (unlike built-in TextEncodeQwenImageEdit)
- KSampler (Efficient) outputs IMAGE at index 5 (not LATENT at index 0 like standard KSampler)
- CLIP type must be "qwen_image" not "stable_diffusion"
- Qwen models are image EDITORS not generators — require an input image
- Resolution must be 1024px, 32px-aligned
