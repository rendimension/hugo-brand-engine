from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import sys
import base64
from io import BytesIO
from urllib.parse import urlparse
import textwrap

print("🧠 Hugo Brand Engine - Python executable:", sys.executable)

app = Flask(__name__)

# === Paths (Railway compatible) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

POST_IMAGE_DIR = os.path.join(BASE_DIR, 'post_image')
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.png')

def pick_existing_path(*candidates: str) -> str:
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return candidates[0] if candidates else ""

# Fonts: prefer repo root, fallback to /fonts
FONT_BOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Montserrat-Bold.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Montserrat-Bold.ttf'),
)

FONT_REG_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Montserrat-Regular.ttf'),
    os.path.join(BASE_DIR, 'Montserrat-VariableFont_wght.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Montserrat-Regular.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Montserrat-VariableFont_wght.ttf'),
)

FONT_SEMIBOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Montserrat-SemiBold.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Montserrat-SemiBold.ttf'),
    FONT_BOLD_PATH,  # fallback to bold
)

# If regular still does not exist but bold does, use bold as fallback
if (not os.path.isfile(FONT_REG_PATH)) and os.path.isfile(FONT_BOLD_PATH):
    FONT_REG_PATH = FONT_BOLD_PATH

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)


# =============================================================================
# CANVAS PRESETS - Hugo Ramirez Brand System
# =============================================================================
# Design Principle: Image = Protagonist, Frame = Support
# Rule: Minimum 70% image visible, maximum 30% frame total
#
# Layout Philosophy:
# - Top bar: Minimal branding, not a banner
# - Image: Dominant, emotional, narrative
# - Bottom: Headline + optional bullets, clean air
# =============================================================================

CANVAS_PRESETS = {
    # =========================================================================
    # LINKEDIN FEED - Primary Hugo format (4:5)
    # 75% image visible
    # =========================================================================
    "linkedin": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 70,           # Reduced from 90 - minimal branding
        "bottom_bar_height": 200,       # Reduced from 240 - cleaner
        "padding": 60,
        "padding_top": 24,              # Vertical centering in bars
        "padding_bottom": 36,
        "brand_font_size": 24,          # Smaller, more elegant
        "tagline_font_size": 14,
        "headline_font_size": 48,       # Strong but not overwhelming
        "bullet_font_size": 26,
        "bullet_gap": 40,
        "max_bullets": 2,               # Maximum 2 bullets
        "max_headline_lines": 2,
    },
    
    # =========================================================================
    # LINKEDIN CAROUSEL - Slide intermedias
    # Concept-strong slides: bigger headline, no bullets
    # =========================================================================
    "carousel": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 60,           # Even more minimal
        "bottom_bar_height": 180,       # Compact
        "padding": 60,
        "padding_top": 20,
        "padding_bottom": 32,
        "brand_font_size": 22,
        "tagline_font_size": 13,
        "headline_font_size": 54,       # Larger for impact
        "bullet_font_size": 26,
        "bullet_gap": 38,
        "max_bullets": 2,
        "max_headline_lines": 2,
    },
    
    # =========================================================================
    # CAROUSEL EDITORIAL - For explanatory slides with more text
    # =========================================================================
    "carousel_text": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 60,
        "bottom_bar_height": 260,       # Slightly larger for text
        "padding": 60,
        "padding_top": 20,
        "padding_bottom": 32,
        "brand_font_size": 22,
        "tagline_font_size": 13,
        "headline_font_size": 44,
        "bullet_font_size": 24,
        "bullet_gap": 36,
        "max_bullets": 3,
        "max_headline_lines": 2,
    },
    
    # =========================================================================
    # INSTAGRAM SQUARE - Prestige/Rendimension
    # Even more minimal - Instagram is visual-first
    # =========================================================================
    "square": {
        "width": 1080,
        "height": 1080,
        "top_bar_height": 55,           # Very minimal
        "bottom_bar_height": 160,       # Compact
        "padding": 55,
        "padding_top": 16,
        "padding_bottom": 28,
        "brand_font_size": 20,
        "tagline_font_size": 12,
        "headline_font_size": 42,
        "bullet_font_size": 24,
        "bullet_gap": 36,
        "max_bullets": 2,
        "max_headline_lines": 2,
    },
    
    # =========================================================================
    # INSTAGRAM VERTICAL - Reels cover or 4:5 post
    # Most minimal - image speaks
    # =========================================================================
    "instagram_vertical": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 50,           # Ultra minimal
        "bottom_bar_height": 160,       # Very compact
        "padding": 55,
        "padding_top": 14,
        "padding_bottom": 28,
        "brand_font_size": 20,
        "tagline_font_size": 12,
        "headline_font_size": 50,       # Strong headline only
        "bullet_font_size": 24,
        "bullet_gap": 34,
        "max_bullets": 0,               # No bullets - headline only
        "max_headline_lines": 2,
    },
    
    # =========================================================================
    # LANDSCAPE - For specific use cases
    # =========================================================================
    "landscape": {
        "width": 1200,
        "height": 675,
        "top_bar_height": 45,
        "bottom_bar_height": 110,
        "padding": 45,
        "padding_top": 12,
        "padding_bottom": 24,
        "brand_font_size": 18,
        "tagline_font_size": 11,
        "headline_font_size": 32,
        "bullet_font_size": 20,
        "bullet_gap": 30,
        "max_bullets": 2,
        "max_headline_lines": 1,
    },
    
    # =========================================================================
    # ULTRA MINIMAL - Maximum image, barely any frame
    # For when image must absolutely dominate
    # =========================================================================
    "minimal": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 0,            # No top bar
        "bottom_bar_height": 140,       # Just headline area
        "padding": 50,
        "padding_top": 0,
        "padding_bottom": 24,
        "brand_font_size": 0,           # No branding
        "tagline_font_size": 0,
        "headline_font_size": 46,
        "bullet_font_size": 0,          # No bullets
        "bullet_gap": 0,
        "max_bullets": 0,
        "max_headline_lines": 2,
    },
}

# Default preset (for Hugo's LinkedIn)
DEFAULT_PRESET = "linkedin"

# =============================================================================
# LEGACY CONSTANTS - For /generate-post backwards compatibility
# =============================================================================
CANVAS_W, CANVAS_H = 1080, 1080
HEADER_H = 120
TEXT_BAND_H = 380
IMG_AREA_Y = HEADER_H
IMG_AREA_H = CANVAS_H - HEADER_H - TEXT_BAND_H
IMG_AREA_X = 0
IMG_AREA_W = CANVAS_W
SAFE_PADDING = 80
TITLE_COLOR = (255, 255, 255)
TITLE_FONT_SIZE = 45
TITLE_X = SAFE_PADDING
TITLE_Y = CANVAS_H - TEXT_BAND_H + 35
BULLET_COLOR = (185, 185, 185)
BULLET_FONT_SIZE = 30
BULLET_GAP_Y = 52
BULLET_DOT_OFFSET_X = 0
BULLET_TEXT_OFFSET_X = 24
BULLET_X = SAFE_PADDING
BULLET_Y = TITLE_Y + 90
TEXT_BAND_OVERLAY = True
BAND_ALPHA = 210


# =============================================================================
# COLOR SCHEMES - Hugo Ramirez Brand Identity
# =============================================================================
# Brand Colors from Landing Page:
# Primary Blue: #0f4c81 (15, 76, 129)
# Executive Navy: #1a1c20 (26, 28, 32)
# Pure Black: #111111 (17, 17, 17)
# Background Light: #fcfcfc (252, 252, 252)
# Slate 400: #94a3b8 (148, 163, 184)
# Slate 500: #64748b (100, 116, 139)
# Slate 600: #475569 (71, 85, 105)

THEMES = {
    "dark": {
        # Main theme - Dark bars with white text (LinkedIn optimized)
        "bar_color": (17, 17, 17),  # #111111 - Pure Black
        "bar_alpha": 235,
        "brand_color": (255, 255, 255),  # White
        "tagline_color": (148, 163, 184),  # Slate 400
        "title_color": (255, 255, 255),  # White
        "headline_color": (255, 255, 255),  # White
        "bullet_color": (203, 213, 225),  # Slate 300
    },
    "executive": {
        # Executive Navy theme - More sophisticated
        "bar_color": (26, 28, 32),  # #1a1c20 - Executive Navy
        "bar_alpha": 240,
        "brand_color": (255, 255, 255),  # White
        "tagline_color": (148, 163, 184),  # Slate 400
        "title_color": (255, 255, 255),  # White
        "headline_color": (255, 255, 255),  # White
        "bullet_color": (203, 213, 225),  # Slate 300
    },
    "brand": {
        # Primary Blue accent theme
        "bar_color": (15, 76, 129),  # #0f4c81 - Primary Blue
        "bar_alpha": 240,
        "brand_color": (255, 255, 255),  # White
        "tagline_color": (203, 213, 225),  # Slate 300
        "title_color": (255, 255, 255),  # White
        "headline_color": (255, 255, 255),  # White
        "bullet_color": (226, 232, 240),  # Slate 200
    },
    "light": {
        # Light theme - for specific use cases
        "bar_color": (244, 244, 245),  # #f4f4f5 - Background Off
        "bar_alpha": 245,
        "brand_color": (26, 28, 32),  # Executive Navy
        "tagline_color": (100, 116, 139),  # Slate 500
        "title_color": (15, 23, 42),  # Slate 900
        "headline_color": (30, 41, 59),  # Slate 800
        "bullet_color": (71, 85, 105),  # Slate 600
    },
    "minimal": {
        # Minimal - very subtle, almost transparent
        "bar_color": (252, 252, 252),  # #fcfcfc - Background Light
        "bar_alpha": 220,
        "brand_color": (17, 17, 17),  # Pure Black
        "tagline_color": (100, 116, 139),  # Slate 500
        "title_color": (15, 23, 42),  # Slate 900
        "headline_color": (26, 28, 32),  # Executive Navy
        "bullet_color": (71, 85, 105),  # Slate 600
    },
}

DEFAULT_THEME = "dark"


# === Utils ===
def clear_folder(folder_path: str):
    if not os.path.isdir(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return
    for name in os.listdir(folder_path):
        try:
            os.remove(os.path.join(folder_path, name))
        except Exception:
            pass


def _ext_from_content_type(ct: str) -> str:
    ct = (ct or '').split(';')[0].strip().lower()
    mapping = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
    }
    return mapping.get(ct, '.jpg')


def _pick_ext(url: str, response) -> str:
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
        return '.jpg' if ext == '.jpeg' else ext
    return _ext_from_content_type(response.headers.get('Content-Type', ''))


def download_image_to_folder(image_url: str, save_folder: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
    }
    resp = requests.get(image_url, headers=headers, timeout=60)
    resp.raise_for_status()
    ext = _pick_ext(image_url, resp)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(save_folder, filename)
    with open(path, 'wb') as f:
        f.write(resp.content)
    return path


def save_base64_image(base64_string: str, save_folder: str) -> str:
    if ',' in base64_string:
        base64_string = base64_string.split(',', 1)[1]

    image_data = base64.b64decode(base64_string)
    img = Image.open(BytesIO(image_data))
    ext = '.png' if (img.format or '').upper() == 'PNG' else '.jpg'
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(save_folder, filename)

    if ext == '.jpg' and img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    img.save(path, format='PNG' if ext == '.png' else 'JPEG', quality=95)
    return path


def load_font(path: str, size: int):
    try:
        if path and os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    except Exception:
        pass
    return ImageFont.load_default()


def fit_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale and crop image to fill target dimensions (cover mode)"""
    iw, ih = img.size
    if iw == 0 or ih == 0:
        return Image.new("RGB", (target_w, target_h), (0, 0, 0))
    scale = max(target_w / iw, target_h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - target_w) // 2)
    top = max(0, (nh - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def normalize_text(text: str, max_length: int = 100) -> str:
    """Clean and truncate text for safe rendering"""
    if not text:
        return ""
    # Remove problematic characters
    text = str(text).strip()
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = text.replace('&', 'and')
    # Truncate with ellipsis if needed
    if len(text) > max_length:
        text = text[:max_length - 3].rsplit(' ', 1)[0] + "..."
    return text


def wrap_text(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list:
    """Wrap text to fit within max_width pixels"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


# =============================================================================
# NEW RENDER FUNCTION - For /render-slide endpoint
# =============================================================================
def render_slide(
    image_path: str,
    preset_name: str = "linkedin",
    theme_name: str = "dark",
    top_text: str = "",
    headline: str = "",
    bullets: list = None,
    brand_name: str = "HUGO RAMIREZ",
    tagline: str = "Strategic Integrator"
) -> str:
    """
    Render a slide with professional layout:
    - Top bar with brand name and tagline (minimal)
    - Main image area (cover fit) - DOMINANT
    - Bottom bar with headline and bullets (clean)
    
    Design Philosophy:
    - Image = Protagonist (70%+ visible)
    - Frame = Support (30% max)
    - Less text = More authority
    
    Returns: tuple (output_path, filename)
    """
    bullets = bullets or []
    
    # Get preset and theme
    preset = CANVAS_PRESETS.get(preset_name, CANVAS_PRESETS["linkedin"])
    theme = THEMES.get(theme_name, THEMES["dark"])
    
    # Canvas dimensions
    width = preset["width"]
    height = preset["height"]
    top_bar_h = preset["top_bar_height"]
    bottom_bar_h = preset["bottom_bar_height"]
    padding = preset["padding"]
    padding_top = preset.get("padding_top", padding // 3)
    padding_bottom = preset.get("padding_bottom", padding // 2)
    
    # Enforce bullet limits from preset
    max_bullets = preset.get("max_bullets", 2)
    max_headline_lines = preset.get("max_headline_lines", 2)
    
    # Limit bullets to preset maximum
    if max_bullets == 0:
        bullets = []
    else:
        bullets = bullets[:max_bullets]
    
    # Calculate image area (should be ~70-80% of canvas)
    img_area_y = top_bar_h
    img_area_h = height - top_bar_h - bottom_bar_h
    
    # Log the proportions for debugging
    image_percentage = (img_area_h / height) * 100
    print(f"🎨 Preset: {preset_name} | Image: {image_percentage:.1f}% | Top: {top_bar_h}px | Bottom: {bottom_bar_h}px")
    
    # Create canvas
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    
    # Load and place main image
    with Image.open(image_path) as src:
        src = src.convert("RGB")
        fitted = fit_cover(src, width, img_area_h)
        canvas.paste(fitted, (0, img_area_y))
    
    # Draw bars with overlay
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    bar_color_rgba = theme["bar_color"] + (theme["bar_alpha"],)
    
    # Top bar (only if height > 0)
    if top_bar_h > 0:
        overlay_draw.rectangle((0, 0, width, top_bar_h), fill=bar_color_rgba)
    
    # Bottom bar
    overlay_draw.rectangle((0, height - bottom_bar_h, width, height), fill=bar_color_rgba)
    
    # Composite overlay
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)
    
    # Load fonts
    brand_font = load_font(FONT_BOLD_PATH, preset["brand_font_size"])
    tagline_font = load_font(FONT_REG_PATH, preset["tagline_font_size"])
    headline_font = load_font(FONT_BOLD_PATH, preset["headline_font_size"])
    bullet_font = load_font(FONT_REG_PATH, preset["bullet_font_size"])
    
    # Draw brand name (top left) - only if top bar exists and font size > 0
    if top_bar_h > 0 and preset["brand_font_size"] > 0:
        brand_y = (top_bar_h - preset["brand_font_size"]) // 2
        draw.text((padding, brand_y), brand_name, font=brand_font, fill=theme["brand_color"])
    
    # Draw tagline (top right) - only if top bar exists
    if top_bar_h > 0 and tagline and preset["tagline_font_size"] > 0:
        tagline_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_width = tagline_bbox[2] - tagline_bbox[0]
        tagline_y = (top_bar_h - preset["tagline_font_size"]) // 2 + 2
        draw.text((width - padding - tagline_width, tagline_y), tagline, font=tagline_font, fill=theme["tagline_color"])
    
    # Calculate bottom section layout
    bottom_start_y = height - bottom_bar_h + padding_bottom
    
    # Draw headline
    if headline and preset["headline_font_size"] > 0:
        headline_clean = normalize_text(headline, max_length=100)
        
        # Wrap headline if needed
        max_text_width = width - (padding * 2)
        headline_lines = wrap_text(headline_clean, headline_font, max_text_width, draw)
        
        # Limit to max lines
        headline_lines = headline_lines[:max_headline_lines]
        
        line_height = preset["headline_font_size"] + 8
        for i, line in enumerate(headline_lines):
            draw.text(
                (padding, bottom_start_y + (i * line_height)),
                line,
                font=headline_font,
                fill=theme["headline_color"]
            )
        
        # Calculate where bullets start
        bullet_start_y = bottom_start_y + (len(headline_lines) * line_height) + 16
    else:
        bullet_start_y = bottom_start_y
    
    # Draw bullets (only if allowed by preset)
    if bullets and preset["bullet_font_size"] > 0 and max_bullets > 0:
        for i, bullet in enumerate(bullets):
            if not bullet or not str(bullet).strip():
                continue
            
            bullet_text = normalize_text(str(bullet), max_length=70)
            bullet_y = bullet_start_y + (i * preset["bullet_gap"])
            
            # Check if bullet would exceed bottom bar
            if bullet_y + preset["bullet_font_size"] > height - padding_bottom:
                break
            
            # Draw bullet point
            draw.text((padding, bullet_y), "•", font=bullet_font, fill=theme["bullet_color"])
            
            # Draw bullet text
            draw.text((padding + 20, bullet_y), bullet_text, font=bullet_font, fill=theme["bullet_color"])
    
    # Save output
    filename = f"slide_{uuid.uuid4().hex}.png"
    output_path = os.path.join(POST_OUTPUT_DIR, filename)
    canvas.convert("RGB").save(output_path, format="PNG", quality=95)
    
    return output_path, filename


# =============================================================================
# LEGACY FUNCTIONS - For /generate-post backwards compatibility
# =============================================================================
def draw_title(draw, title: str, font):
    draw.text((TITLE_X, TITLE_Y), title, font=font, fill=TITLE_COLOR)


def draw_bullets(draw, bullets: list, font):
    for i, text in enumerate(bullets):
        if not text or not str(text).strip():
            continue
        line_y = BULLET_Y + (i * BULLET_GAP_Y)
        draw.text((BULLET_X + BULLET_DOT_OFFSET_X, line_y), "•", font=font, fill=BULLET_COLOR)
        draw.text((BULLET_X + BULLET_TEXT_OFFSET_X, line_y), str(text).strip(), font=font, fill=BULLET_COLOR)


def draw_text_section(canvas: Image.Image, title: str, bullets: list):
    title_font = load_font(FONT_BOLD_PATH, TITLE_FONT_SIZE)
    bullet_font = load_font(FONT_BOLD_PATH, BULLET_FONT_SIZE)

    if TEXT_BAND_OVERLAY:
        band_y = CANVAS_H - TEXT_BAND_H
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.rectangle((0, band_y, CANVAS_W, CANVAS_H), fill=(0, 0, 0, BAND_ALPHA))
        canvas_alpha = canvas.convert("RGBA")
        canvas_rgba = Image.alpha_composite(canvas_alpha, overlay)
        canvas.paste(canvas_rgba.convert("RGB"))

    draw = ImageDraw.Draw(canvas)
    draw_title(draw, title, title_font)
    draw_bullets(draw, bullets, bullet_font)


# =============================================================================
# ROUTES
# =============================================================================
@app.route("/")
def home():
    return jsonify({
        "service": "Hugo Brand Engine",
        "version": "2.0",
        "company": "Hugo Ramirez - Strategic Integrator",
        "status": "running",
        "brand_colors": {
            "primary_blue": "#0f4c81",
            "executive_navy": "#1a1c20",
            "pure_black": "#111111",
            "background_light": "#fcfcfc"
        },
        "features": [
            "Accepts image_url OR image_base64",
            "Multiple canvas presets (carousel, square, landscape)",
            "5 brand-consistent themes (dark, executive, brand, light, minimal)",
            "Auto text wrapping and normalization",
            "Professional typography with Montserrat"
        ],
        "endpoints": {
            "health": "/health",
            "generate_legacy": "POST /generate-post (backwards compatible)",
            "render_slide": "POST /render-slide (new - for carousels)"
        },
        "presets": list(CANVAS_PRESETS.keys()),
        "themes": list(THEMES.keys())
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "version": "2.0",
        "service": "Hugo Brand Engine",
        "template_exists": os.path.isfile(TEMPLATE_PATH),
        "post_image_dir": os.path.isdir(POST_IMAGE_DIR),
        "post_output_dir": os.path.isdir(POST_OUTPUT_DIR),
        "fonts": {
            "bold": {"path": FONT_BOLD_PATH, "exists": os.path.isfile(FONT_BOLD_PATH)},
            "regular": {"path": FONT_REG_PATH, "exists": os.path.isfile(FONT_REG_PATH)},
            "semibold": {"path": FONT_SEMIBOLD_PATH, "exists": os.path.isfile(FONT_SEMIBOLD_PATH)},
        },
        "presets": CANVAS_PRESETS,
        "themes": list(THEMES.keys())
    }), 200


@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)


# =============================================================================
# NEW ENDPOINT - /render-slide
# =============================================================================
@app.route("/render-slide", methods=["POST"])
def render_slide_endpoint():
    """
    New endpoint for carousel/multi-image generation.
    
    Expected payload:
    {
        "image_url": "https://...",           # OR image_base64
        "image_base64": "base64string...",    # OR image_url
        "preset": "carousel",                  # carousel | square | landscape
        "theme": "dark",                       # dark | light
        "brand_name": "HUGO RAMIREZ",         # optional
        "tagline": "Strategic Integrator",    # optional
        "headline": "Main message here",      # optional
        "bullets": ["Point 1", "Point 2"]     # optional, max 4
    }
    
    Returns:
    {
        "status": "success",
        "filename": "slide_xxx.png",
        "download_url": "https://.../post_output/slide_xxx.png",
        "preset": "carousel",
        "theme": "dark"
    }
    """
    payload = request.get_json(silent=True)
    if isinstance(payload, list) and payload:
        payload = payload[0]
    
    if not isinstance(payload, dict):
        return jsonify({"error": "Expected JSON object"}), 400
    
    # Get image source
    image_url = payload.get("image_url") or payload.get("image")
    image_base64 = payload.get("image_base64") or payload.get("imageBase64") or payload.get("base64")
    
    if not image_url and not image_base64:
        return jsonify({"error": "Either image_url or image_base64 is required"}), 400
    
    # Get options
    preset_name = payload.get("preset", "linkedin").lower()
    theme_name = payload.get("theme", "dark").lower()
    
    if preset_name not in CANVAS_PRESETS:
        preset_name = "linkedin"
    if theme_name not in THEMES:
        theme_name = "dark"
    
    # Get text content
    brand_name = payload.get("brand_name", "HUGO RAMIREZ")
    tagline = payload.get("tagline", "Strategic Integrator")
    headline = payload.get("headline", "")
    bullets = payload.get("bullets", [])
    
    # Also support legacy format
    if not headline and payload.get("title"):
        headline = payload.get("title")
    if not bullets:
        b1 = payload.get("bullet1") or payload.get("bullet_1", "")
        b2 = payload.get("bullet2") or payload.get("bullet_2", "")
        b3 = payload.get("bullet3") or payload.get("bullet_3", "")
        bullets = [b for b in [b1, b2, b3] if b]
    
    # Download/save image
    clear_folder(POST_IMAGE_DIR)
    
    try:
        if image_base64:
            image_path = save_base64_image(image_base64, POST_IMAGE_DIR)
        else:
            image_path = download_image_to_folder(image_url, POST_IMAGE_DIR)
    except Exception as e:
        return jsonify({"error": f"Failed to process image: {e}"}), 400
    
    # Render slide
    try:
        output_path, filename = render_slide(
            image_path=image_path,
            preset_name=preset_name,
            theme_name=theme_name,
            headline=headline,
            bullets=bullets,
            brand_name=brand_name,
            tagline=tagline
        )
        
        base_url = request.url_root.rstrip('/')
        download_url = f"{base_url}/post_output/{filename}"
        
        return jsonify({
            "status": "success",
            "filename": filename,
            "output": output_path,
            "download_url": download_url,
            "png_url": download_url,  # Alias for compatibility
            "preset": preset_name,
            "theme": theme_name,
            "source": "base64" if image_base64 else "url"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Render failed: {e}"}), 500


# =============================================================================
# LEGACY ENDPOINT - /generate-post (backwards compatible)
# =============================================================================
@app.route("/generate-post", methods=["POST"])
def generate_post():
    """
    Legacy endpoint for Rendimension - kept for backwards compatibility.
    """
    payload = request.get_json(silent=True)
    if isinstance(payload, list) and payload:
        payload = payload[0]

    if not isinstance(payload, dict):
        return jsonify({"error": "Expected JSON object"}), 400

    image_url = payload.get("image_url") or payload.get("image") or payload.get("image_1")
    image_base64 = payload.get("image_base64") or payload.get("imageBase64") or payload.get("base64")

    title = (payload.get("title", "") or "").strip()
    b1 = payload.get("bullet1", "") or payload.get("bullet_1", "")
    b2 = payload.get("bullet2", "") or payload.get("bullet_2", "")
    b3 = payload.get("bullet3", "") or payload.get("bullet_3", "")

    if not image_url and not image_base64:
        return jsonify({"error": "Either image_url or image_base64 is required"}), 400

    if not title:
        return jsonify({"error": "title is required"}), 400

    if not os.path.isfile(TEMPLATE_PATH):
        return jsonify({"error": f"template.png not found at {TEMPLATE_PATH}"}), 500

    clear_folder(POST_IMAGE_DIR)

    try:
        if image_base64:
            downloaded_path = save_base64_image(image_base64, POST_IMAGE_DIR)
        else:
            downloaded_path = download_image_to_folder(image_url, POST_IMAGE_DIR)
    except Exception as e:
        return jsonify({"error": f"Failed to process image: {e}"}), 400

    try:
        template = Image.open(TEMPLATE_PATH).convert("RGB")
        if template.size != (CANVAS_W, CANVAS_H):
            template = template.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)

        with Image.open(downloaded_path) as src:
            src = src.convert("RGB")
            area = fit_cover(src, IMG_AREA_W, IMG_AREA_H)
            template.paste(area, (IMG_AREA_X, IMG_AREA_Y))

        draw_text_section(template, title, [b1, b2, b3])

        filename = f"post_rendimension_{uuid.uuid4().hex}.jpg"
        out_path = os.path.join(POST_OUTPUT_DIR, filename)
        template.save(out_path, format="JPEG", quality=95)

        base_url = request.url_root.rstrip('/')
        download_url = f"{base_url}/post_output/{filename}"

        return jsonify({
            "status": "success",
            "company": "rendimension",
            "filename": filename,
            "output": out_path,
            "download_url": download_url,
            "source": "base64" if image_base64 else "url"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Composition failed: {e}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
