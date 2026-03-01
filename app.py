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

# Fonts: Inter Official Brand System
# Hierarchy:
# - ExtraBold (800): H1 Headlines
# - Bold (700): H2 Secondary headlines  
# - SemiBold (600): Labels, Brand text
# - Medium (500): Bullets, body text

FONT_EXTRABOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Inter-ExtraBold.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Inter-ExtraBold.ttf'),
)

FONT_BOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Inter-Bold.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Inter-Bold.ttf'),
)

FONT_SEMIBOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Inter-SemiBold.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Inter-SemiBold.ttf'),
)

FONT_MEDIUM_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Inter-Medium.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Inter-Medium.ttf'),
)

# Fallback chain
FONT_REG_PATH = FONT_MEDIUM_PATH if os.path.isfile(FONT_MEDIUM_PATH) else FONT_BOLD_PATH

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)


# =============================================================================
# CANVAS PRESETS - Hugo Ramirez Official Brand System
# =============================================================================
# Design Principles:
# - Image = Protagonist (minimum 75% visible)
# - Frame = Support (maximum 25% total)
# - Typography: Inter only, strict hierarchy
# - Tracking: H1 -0.02em, Labels +0.25em
#
# Typography Hierarchy:
# - H1 (Headlines): Inter ExtraBold 800, 54px, tracking -0.02em
# - H2 (Secondary): Inter Bold 700, tracking -0.01em
# - Bullets: Inter Medium 500, 28px, tracking 0
# - Labels: Inter SemiBold 600, uppercase, tracking +0.25em
# =============================================================================

CANVAS_PRESETS = {
    # =========================================================================
    # LINKEDIN OFFICIAL V2 - Primary Hugo format (4:5)
    # Canvas: 1080x1350 | LARGE TEXT for mobile readability
    # =========================================================================
    "linkedin": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 100,          # Increased for visibility
        "bottom_bar_height": 300,       # Increased for larger text
        "padding": 60,
        "padding_top": 32,
        "padding_bottom": 44,
        # Typography - LARGE for mobile
        "brand_font_size": 38,          # MUCH LARGER - was 20
        "brand_tracking": 0.25,
        "tagline_font_size": 0,
        "headline_font_size": 68,       # MUCH LARGER - was 54
        "headline_tracking": -0.02,
        "bullet_font_size": 40,         # MUCH LARGER - was 28
        "bullet_gap": 54,
        "max_bullets": 3,
        "max_headline_lines": 2,
        "max_headline_chars": 50,
        "max_bullet_chars": 45,
    },
    # =========================================================================
    # LINKEDIN MINIMAL - Even cleaner, for strong images
    # =========================================================================
    "linkedin_minimal": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 70,           # Reduced
        "bottom_bar_height": 200,       # Compact
        "padding": 70,
        "padding_top": 25,
        "padding_bottom": 36,
        "brand_font_size": 18,
        "brand_tracking": 0.25,
        "tagline_font_size": 0,
        "headline_font_size": 50,
        "headline_tracking": -0.02,
        "bullet_font_size": 26,
        "bullet_gap": 40,
        "max_bullets": 2,
        "max_headline_lines": 2,
        "max_headline_chars": 50,
        "max_bullet_chars": 50,
    },
    
    # =========================================================================
    # CAROUSEL - For carousel slides (concept-strong)
    # LARGE TEXT for mobile readability
    # =========================================================================
    "carousel": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 100,          # Increased for visibility
        "bottom_bar_height": 280,       # Increased for larger text
        "padding": 60,
        "padding_top": 32,
        "padding_bottom": 44,
        "brand_font_size": 36,          # MUCH LARGER - was 18
        "brand_tracking": 0.25,
        "tagline_font_size": 0,
        "headline_font_size": 72,       # MUCH LARGER - was 56
        "headline_tracking": -0.02,
        "bullet_font_size": 42,         # MUCH LARGER - was 26
        "bullet_gap": 56,
        "max_bullets": 2,
        "max_headline_lines": 2,
        "max_headline_chars": 45,
        "max_bullet_chars": 40,
    },
    
    # =========================================================================
    # CAROUSEL TEXT - For explanatory slides with more content
    # =========================================================================
    "carousel_text": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 70,
        "bottom_bar_height": 280,
        "padding": 70,
        "padding_top": 24,
        "padding_bottom": 36,
        "brand_font_size": 18,
        "brand_tracking": 0.25,
        "tagline_font_size": 0,
        "headline_font_size": 46,
        "headline_tracking": -0.01,
        "bullet_font_size": 26,
        "bullet_gap": 40,
        "max_bullets": 3,
        "max_headline_lines": 2,
        "max_headline_chars": 60,
        "max_bullet_chars": 55,
    },
    
    # =========================================================================
    # INSTAGRAM SQUARE - Prestige/Rendimension
    # LARGE TEXT for mobile readability
    # =========================================================================
    "square": {
        "width": 1080,
        "height": 1080,
        "top_bar_height": 90,
        "bottom_bar_height": 240,
        "padding": 55,
        "padding_top": 28,
        "padding_bottom": 36,
        "brand_font_size": 32,          # LARGER
        "brand_tracking": 0.25,
        "tagline_font_size": 0,
        "headline_font_size": 60,       # LARGER
        "headline_tracking": -0.02,
        "bullet_font_size": 36,         # LARGER
        "bullet_gap": 48,
        "max_bullets": 2,
        "max_headline_lines": 2,
        "max_headline_chars": 40,
        "max_bullet_chars": 40,
    },
    
    # =========================================================================
    # INSTAGRAM VERTICAL - Reels cover or 4:5 post
    # Most minimal - headline only
    # =========================================================================
    "instagram_vertical": {
        "width": 1080,
        "height": 1350,
        "top_bar_height": 60,
        "bottom_bar_height": 180,
        "padding": 60,
        "padding_top": 20,
        "padding_bottom": 32,
        "brand_font_size": 16,
        "brand_tracking": 0.25,
        "tagline_font_size": 0,
        "headline_font_size": 52,
        "headline_tracking": -0.02,
        "bullet_font_size": 24,
        "bullet_gap": 36,
        "max_bullets": 0,               # No bullets - headline only
        "max_headline_lines": 2,
        "max_headline_chars": 45,
        "max_bullet_chars": 0,
    },
    
    # =========================================================================
    # LANDSCAPE - Horizontal format
    # =========================================================================
    "landscape": {
        "width": 1200,
        "height": 675,
        "top_bar_height": 50,
        "bottom_bar_height": 120,
        "padding": 50,
        "padding_top": 16,
        "padding_bottom": 26,
        "brand_font_size": 16,
        "brand_tracking": 0.25,
        "tagline_font_size": 0,
        "headline_font_size": 36,
        "headline_tracking": -0.02,
        "bullet_font_size": 22,
        "bullet_gap": 32,
        "max_bullets": 2,
        "max_headline_lines": 1,
        "max_headline_chars": 45,
        "max_bullet_chars": 40,
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
# Official Brand Colors:
# Primary Navy: #0F1A2B (15, 26, 43) - Top bar, frames
# Executive Navy: #1a1c20 (26, 28, 32) - Alternative
# Pure Black: #111111 (17, 17, 17) - Deep dark
# Primary Blue: #0f4c81 (15, 76, 129) - Accent
# Background Light: #fcfcfc (252, 252, 252)

THEMES = {
    "dark": {
        # Official Hugo Brand - Navy Deep
        "bar_color": (15, 26, 43),  # #0F1A2B - Primary Navy (official)
        "bar_alpha": 255,  # Solid, no transparency
        "brand_color": (255, 255, 255),  # White
        "tagline_color": (148, 163, 184),  # Slate 400
        "headline_color": (255, 255, 255),  # White
        "bullet_color": (203, 213, 225),  # Slate 300
    },
    "executive": {
        # Executive Navy theme
        "bar_color": (26, 28, 32),  # #1a1c20 - Executive Navy
        "bar_alpha": 255,
        "brand_color": (255, 255, 255),
        "tagline_color": (148, 163, 184),
        "headline_color": (255, 255, 255),
        "bullet_color": (203, 213, 225),
    },
    "brand": {
        # Primary Blue accent theme
        "bar_color": (15, 76, 129),  # #0f4c81 - Primary Blue
        "bar_alpha": 255,
        "brand_color": (255, 255, 255),
        "tagline_color": (203, 213, 225),
        "headline_color": (255, 255, 255),
        "bullet_color": (226, 232, 240),
    },
    "pure_black": {
        # Pure black for maximum contrast
        "bar_color": (17, 17, 17),  # #111111
        "bar_alpha": 255,
        "brand_color": (255, 255, 255),
        "tagline_color": (148, 163, 184),
        "headline_color": (255, 255, 255),
        "bullet_color": (203, 213, 225),
    },
    "light": {
        # Light theme - for dark images
        "bar_color": (244, 244, 245),  # #f4f4f5
        "bar_alpha": 250,
        "brand_color": (15, 26, 43),  # Navy
        "tagline_color": (100, 116, 139),
        "headline_color": (15, 23, 42),
        "bullet_color": (71, 85, 105),
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
    
    # Load fonts with correct weights per hierarchy
    # Brand text: SemiBold (600) - for top bar label
    brand_font = load_font(FONT_SEMIBOLD_PATH, preset["brand_font_size"])
    
    # Headlines: ExtraBold (800) - for H1
    headline_font = load_font(FONT_EXTRABOLD_PATH, preset["headline_font_size"])
    
    # Bullets: Medium (500) - for body text
    bullet_font = load_font(FONT_MEDIUM_PATH, preset["bullet_font_size"])
    
    # Draw brand name (top left) - UPPERCASE with tracking
    # Label style: SemiBold, uppercase, tracking +0.25em
    if top_bar_h > 0 and preset["brand_font_size"] > 0:
        brand_y = (top_bar_h - preset["brand_font_size"]) // 2
        brand_text = brand_name.upper()  # Always uppercase for labels
        draw.text((padding, brand_y), brand_text, font=brand_font, fill=theme["brand_color"])
    
    # Note: Tagline removed from official system for cleaner look
    # Top bar is now just the brand label (uppercase, minimal)
    
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
