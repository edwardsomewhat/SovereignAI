# Title Text + Border Post-Processing

Pattern for adding centered title text and classy borders to generated poster images using PIL.

## Proven: Broncos "Mile High" Poster (May 2026)

Flux Dev fp8 txt2img → PIL overlay "MILE HIGH" text + dual border. Final: 1366×790, ~1.4MB. Scored 10/10 on review.

## When to Use

When the task calls for:
- A poster/ad with a **title or call-to-action** at the bottom
- A **classy framed border** around the image
- Text that ComfyUI can't reliably generate (all text)

## Recipe

```python
from PIL import Image, ImageDraw, ImageFont

# Load generated image
img = Image.open("generated.png").convert("RGB")
W, H = img.size

# ── STEP 1: Expand canvas for border ──
BORDER_OUTER = 8   # thick dark frame
BORDER_INNER = 3   # thin accent stripe
PADDING = BORDER_OUTER + BORDER_INNER

new_w, new_h = W + 2*PADDING, H + 2*PADDING
canvas = Image.new("RGB", (new_w, new_h), "#001a33")  # dark navy outer
draw = ImageDraw.Draw(canvas)

# Inner orange stripe
draw.rectangle(
    [BORDER_OUTER, BORDER_OUTER, new_w-BORDER_OUTER-1, new_h-BORDER_OUTER-1],
    outline="#FF6600",
    width=BORDER_INNER
)

# Paste image into framed canvas
canvas.paste(img, (PADDING, PADDING))

# ── STEP 2: Add title text ──
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TEXT = "MILE HIGH"
FONT_SIZE = 130
TEXT_COLOR = "#FF6600"      # bright orange
OUTLINE_COLOR = "black"
OUTLINE_WIDTH = 4

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
draw = ImageDraw.Draw(canvas)

# Measure and center
bbox = draw.textbbox((0, 0), TEXT, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
x = (new_w - tw) // 2
y = new_h - th - 40  # 40px from bottom

# 8-direction outline for legibility on any background
for dx, dy in [
    (-OUTLINE_WIDTH, 0), (OUTLINE_WIDTH, 0), (0, -OUTLINE_WIDTH), (0, OUTLINE_WIDTH),
    (-OUTLINE_WIDTH, -OUTLINE_WIDTH), (OUTLINE_WIDTH, -OUTLINE_WIDTH),
    (-OUTLINE_WIDTH, OUTLINE_WIDTH), (OUTLINE_WIDTH, OUTLINE_WIDTH)
]:
    draw.text((x + dx, y + dy), TEXT, font=font, fill=OUTLINE_COLOR)
draw.text((x, y), TEXT, font=font, fill=TEXT_COLOR)

# ── STEP 3: Save ──
canvas.save("final.png")
print(f"Saved: {new_w}×{new_h}")
```

## Border Color Combinations

| Style | Outer | Inner | Use Case |
|-------|-------|-------|----------|
| **Navy + Orange** | #001a33 (navy) | #FF6600 (orange) | Sports, Broncos, bold |
| **Gold + Black** | black | #FFD700 (gold) | Premium, elegant |
| **White + Brand** | white | brand primary | Clean, modern |
| **Dark + Accent** | #111111 | brand accent | Sleek, luxury |

## Font Sizing (for 1344×768 base)

| Element | Font Size | Color | Outline |
|---------|-----------|-------|---------|
| Large title (bottom) | 120-150px | Bright brand color | 4px black |
| Subtitle | 50-70px | White | 3px black |
| Small text | 30-45px | White | 2px black |

Always verify with qwen3-vl:8b review: text legible? correctly spelled? border looks classy?
