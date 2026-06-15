"""
Copy Tools — Text creative generation and humanization.

generate_copy: Taglines, ad copy, social posts, product descriptions
humanize: Strips AI cliches from any text
"""
import json
import os
from urllib.request import Request, urlopen
from crewai.tools import tool

OLLAMA_HQ = "http://100.84.92.74:11434"
VLLM_CONCHAI = "http://100.69.153.16:8020/v1"

# Default humanizer replacements — AI-isms to strip
AI_ISMS = [
    ("dive into", "explore"),
    ("unlock", "get"),
    ("empower", "give"),
    ("game-changing", "important"),
    ("revolutionary", "new"),
    ("cutting-edge", "advanced"),
    ("leverage", "use"),
    ("synergize", "combine"),
    ("paradigm shift", "big change"),
    ("best-in-class", "top-tier"),
    ("state-of-the-art", "modern"),
    ("robust", "solid"),
    ("seamless", "smooth"),
    ("holistic", "complete"),
    ("journey", "path"),
    ("ecosystem", "network"),
    ("democratize", "open up"),
    ("transformative", "useful"),
    ("next-generation", "new"),
    ("groundbreaking", "novel"),
]


def _local_generate(system: str, user: str, model: str = "gpt-oss:20b") -> str:
    """Generate text using a local Ollama model on hq-ai."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 512},
    }
    req = Request(
        f"{OLLAMA_HQ}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read()).get("message", {}).get("content", "")
    except Exception as e:
        return f"❌ Copy generation failed: {e}"


@tool("generate_copy")
def generate_copy(
    brief: str,
    copy_type: str = "tagline",
    count: int = 3,
    tone: str = "confident, warm, anti-subscription",
) -> str:
    """
    Generate marketing copy using local LLM on hq-ai (gpt-oss:20b).

    Types: tagline, ad_copy, social_post, product_description, script, brand_name.

    Writes in SovereignAI voice: confident, warm, technical, anti-subscription.
    Core message: "The absence of reliance is freedom."

    Args:
        brief: What the copy is for. Include context, audience, key message.
        copy_type: Type of copy to generate.
        count: How many variations to produce.
        tone: Desired tone (defaults to SovereignAI voice).

    Returns:
        Numbered copy options with creative rationale.
    """
    type_guides = {
        "tagline": "3-8 words. Memorable, punchy. Each option a different angle.",
        "ad_copy": "Headline + body (2-3 sentences) + CTA. Persuasive, benefit-focused.",
        "social_post": "1-3 sentences. Platform-ready. Hashtag suggestions at end.",
        "product_description": "2-4 sentences. Features → benefits. Technical but warm.",
        "script": "Timed to duration. Natural speech cadence. Scene directions in [brackets].",
        "brand_name": "1-3 words. Available .com if possible. Explain the vibe.",
    }

    guide = type_guides.get(copy_type, type_guides["tagline"])

    system = f"""You are a senior copywriter at SovereignAI. Tone: {tone}.
Voice rules:
- No AI cliches ever (no "unlock," "empower," "game-changing," "dive into," "revolutionary")
- Short sentences. Active voice. Be specific, not abstract.
- Anti-subscription ethos: "The absence of reliance is freedom."
- Confident but not arrogant. Technical but accessible.

Format: {guide}"""

    user = f"Brief: {brief}\n\nGenerate exactly {count} distinct {copy_type} options. Each a different angle, rhythm, or emotional hook. Number them."

    result = _local_generate(system, user)

    lines = [
        f"✍️ {copy_type.replace('_', ' ').title()} — {count} options",
        f"Brief: {brief}",
        f"Tone: {tone}",
        "",
        result,
    ]
    return "\n".join(lines)


@tool("humanize")
def humanize(
    text: str,
) -> str:
    """
    Strip AI cliches and make text sound human-written.

    Replaces overused AI vocabulary (unlock, empower, game-changing, etc.)
    and smooths unnatural phrasing. Use on any AI-generated text before delivery.

    Args:
        text: The text to humanize.

    Returns:
        Humanized version of the text.
    """
    result = text
    replacements_made = []

    for bad, good in AI_ISMS:
        if bad in result.lower():
            result = result.replace(bad, good)
            result = result.replace(bad.title(), good.title())
            result = result.replace(bad.upper(), good.upper())
            replacements_made.append(f"'{bad}' → '{good}'")

    # Also strip common AI sentence patterns
    result = result.replace("It is important to note that", "")
    result = result.replace("It should be noted that", "")
    result = result.replace("It is worth mentioning that", "")

    lines = ["🧠 Humanized Text"]
    if replacements_made:
        lines.append(f"Replacements: {len(replacements_made)}")
        lines.append("─" * 40)
    lines.append(result)

    return "\n".join(lines)
