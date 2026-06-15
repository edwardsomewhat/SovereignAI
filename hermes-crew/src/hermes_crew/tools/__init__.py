"""Coding, infrastructure, and creative tools for CrewAI agents."""

from .antigravity_tool import AntigravityTool
from .ollama_code_tool import OllamaCodeTool
from .opencode_tool import OpenCodeTool
from .shinobi_tool import ShinobiTool
from .node_ssh_tool import run_node_command, health_check_all
from .dockhand_tool import list_environments, list_containers, manage_container, deploy_stack

# Generation tools
from .comfyui_image_tool import txt2img, img2img, upscale, inpaint, comfyui_status
from .comfyui_video_tool import txt2video, img2video

# Editor tools
from .editor_tools import (
    review_image, review_video, florence_mask,
    text_overlay, background_remove, color_correct,
)

# Scout tools
from .scout_tools import web_search, web_fetch

# Copy tools
from .copy_tools import generate_copy, humanize

__all__ = [
    # Infrastructure
    "AntigravityTool", "OllamaCodeTool", "OpenCodeTool", "ShinobiTool",
    "run_node_command", "health_check_all",
    "list_environments", "list_containers", "manage_container", "deploy_stack",
    # Generation
    "txt2img", "img2img", "upscale", "inpaint",
    "txt2video", "img2video",
    "comfyui_status",
    # Editor
    "review_image", "review_video", "florence_mask",
    "text_overlay", "background_remove", "color_correct",
    # Copy
    "generate_copy", "humanize",
    # Scout
    "web_search", "web_fetch",
]
