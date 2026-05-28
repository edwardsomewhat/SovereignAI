# Poster & Text Overlay Compositing

Pattern for adding legible text to generated images using PIL/Pillow.

## Problem

SDXL/Flux cannot reliably generate readable text in images. Text must be overlaid in a separate compositing step using PIL.

## Requirements

### Image Background
- **Minimum brightness: 100/255** for white/gold text visibility
- Prompt for "bright, well-lit, high-contrast" backgrounds
- Explicitly request dark/empty regions at top and bottom for text placement
- Avoid "dark, moody, atmospheric" for poster backgrounds

### Text Rendering
- **Always use outlines** (3-4px black) for visibility on any background
- Gold (#FFD700) text with black outlines works on medium-dark backgrounds
- White text with thick black outlines works on any background
- DejaVu Sans Bold widely available on Linux

## PIL Compositing Recipe

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.open("background.png")
draw = ImageDraw.Draw(img)
W, H = img.size

font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def draw_text_with_outline(text, y, font_size, color, outline_color="black", outline_width=3):
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x = (W - tw) // 2
    
    # 8-direction outline
    for dx, dy in [(-outline_width,0), (outline_width,0), (0,-outline_width), (0,outline_width),
                   (-outline_width,-outline_width), (outline_width,-outline_width),
                   (-outline_width,outline_width), (outline_width,outline_width)]:
        draw.text((x+dx, y+dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=color)
    return th

# Layout — stack elements from top with spacing
y = int(H * 0.12)  # Start 12% from top
spacing = int(H * 0.03)

# Title (gold, thick outline)
th = draw_text_with_outline("EVENT NAME", y, int(W * 0.13), "#FFD700", "black", 4)
y += th + spacing//2

# Tagline (white)
th = draw_text_with_outline("Tagline here", y, int(W * 0.05), "white", "black", 2)
# ... continue stacking
```

## Font Sizing Reference (768px wide poster)

| Element | Font Size | Color | Outline |
|---------|-----------|-------|---------|
| Event name | ~100px (W×0.13) | Gold #FFD700 | 4px black |
| Tagline | ~38px (W×0.05) | White | 2px black |
| Date/location | ~45px (W×0.06) | White/Gold | 2px black |
| CTA | ~42px (W×0.055) | Gold | 3px black |

## Verification

After compositing, send through vision model (qwen3-vl:8b) to check:
- All text legible
- Spelling correct
- Colors have enough contrast
- Overall professional appearance
