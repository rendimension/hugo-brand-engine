from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import sys
import base64
from io import BytesIO
from urllib.parse import urlparse

print("🧠 Hugo Brand Engine v2.3 - All Fixes Applied")

app = Flask(__name__)

# === Paths (Railway compatible) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

POST_IMAGE_DIR = os.path.join(BASE_DIR, 'post_image')
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')

def pick_existing_path(*candidates: str) -> str:
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return candidates[0] if candidates else ""

# Fonts: Inter Official Brand System
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

FONT_REGULAR_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Inter-Regular.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Inter-Regular.ttf'),
    FONT_MEDIUM_PATH,  # fallback to medium if regular not found
)

FONT_LIGHT_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'Inter-Light.ttf'),
    os.path.join(BASE_DIR, 'fonts', 'Inter-Light.ttf'),
    FONT_REGULAR_PATH,  # fallback
)

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)


# =============================================================================
# HUGO RAMIREZ - LINKEDIN CAROUSEL DESIGN SYSTEM
# =============================================================================
# Exact specifications from Canva design
# Canvas: 1080 x 1350 px
# Fixed: Proper gradient opacity, balanced font sizes, letter spacing
# =============================================================================

DESIGN_SYSTEM = {
    "carousel": {
        # Canvas
        "width": 1080,
        "height": 1350,
        
        # Header (Top gradient bar)
        # Canva: Linear gradient 180°, 10% opacity
        "header_height": 108,
        "header_gradient_color1": (0, 0, 0, 0),       # Top: transparent
        "header_gradient_color2": (0, 0, 0, 25),      # Bottom: 10% black (255 * 0.10 = 25)
        
        # Footer (Bottom gradient bar)
        # Canva: Linear gradient 180°, 30% opacity
        "footer_start": 1167,
        "footer_height": 183,
        "footer_gradient_color1": (0, 0, 0, 0),       # Top: transparent
        "footer_gradient_color2": (0, 0, 0, 77),      # Bottom: 30% black (255 * 0.30 = 77)
        
        # Content margins
        "margin_left": 108,
        "margin_right": 108,
        "content_width": 864,
        
        # Typography - Header
        "brand_font": "extrabold",
        "brand_size": 48,              # Balanced size
        "brand_letter_spacing": 3,     # Pixels between letters (subtle)
        "brand_y": 35,
        "brand_color": (255, 255, 255),
        
        "tagline_font": "medium",      # Changed from "regular" to "medium" (more reliable)
        "tagline_size": 24,            # Smaller than brand
        "tagline_y": 45,
        "tagline_color": (255, 255, 255),
        
        # Typography - Footer
        "title_font": "semibold",
        "title_size": 44,              # Balanced size
        "title_y": 1200,
        "title_color": (255, 255, 255),
        
        "subtitle_font": "light",
        "subtitle_size": 34,           # Slightly smaller than title
        "subtitle_y": 1260,
        "subtitle_color": (255, 255, 255, 200),  # Slightly transparent
    }
}

# Preset aliases
DESIGN_SYSTEM["linkedin"] = DESIGN_SYSTEM["carousel"]
DESIGN_SYSTEM["square"] = {
    **DESIGN_SYSTEM["carousel"],
    "width": 1080,
    "height": 1080,
    "footer_start": 897,
    "footer_height": 183,
    "title_y": 920,
    "subtitle_y": 980,
}


def load_font(font_type: str, size: int):
    """Load font by type with fallback and debug logging"""
    font_paths = {
        "extrabold": FONT_EXTRABOLD_PATH,
        "bold": FONT_BOLD_PATH,
        "semibold": FONT_SEMIBOLD_PATH,
        "medium": FONT_MEDIUM_PATH,
        "regular": FONT_REGULAR_PATH,
        "light": FONT_LIGHT_PATH,
    }
    
    path = font_paths.get(font_type, FONT_MEDIUM_PATH)
    
    # Debug: Check if font exists
    if path and os.path.isfile(path):
        print(f"✅ Font {font_type} loaded from {path}")
        try:
            return ImageFont.truetype(path, size)
        except Exception as e:
            print(f"❌ Font load error for {font_type}: {e}")
    else:
        print(f"❌ Font {font_type} NOT found at {path}")
    
    # Fallback chain
    fallback_paths = [FONT_BOLD_PATH, FONT_MEDIUM_PATH, FONT_SEMIBOLD_PATH]
    for fallback in fallback_paths:
        if fallback and os.path.isfile(fallback):
            print(f"⚠️ Using fallback font: {fallback}")
            try:
                return ImageFont.truetype(fallback, size)
            except:
                continue
    
    # Last resort: system font or default
    print("⚠️ Using PIL default font (last resort)")
    try:
        # Try DejaVu on Linux (Railway)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()


def create_gradient(width: int, height: int, color1: tuple, color2: tuple) -> Image.Image:
    """Create a vertical gradient from color1 (top) to color2 (bottom)"""
    gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    for y in range(height):
        factor = y / height if height > 0 else 0
        
        r = int(color1[0] + (color2[0] - color1[0]) * factor)
        g = int(color1[1] + (color2[1] - color1[1]) * factor)
        b = int(color1[2] + (color2[2] - color1[2]) * factor)
        a = int(color1[3] + (color2[3] - color1[3]) * factor)
        
        for x in range(width):
            gradient.putpixel((x, y), (r, g, b, a))
    
    return gradient


def fit_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale and crop image to fill target dimensions (CSS object-fit: cover)"""
    img_w, img_h = img.size
    scale = max(target_w / img_w, target_h / img_h)
    
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    
    return img.crop((left, top, left + target_w, top + target_h))


def draw_text_with_spacing(draw, position, text, font, fill, letter_spacing=0):
    """Draw text with custom letter spacing (pixel by pixel)"""
    x, y = position
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        # Get character width and advance
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        x += char_width + letter_spacing


def render_slide_v2(
    image_path: str,
    preset_name: str = "carousel",
    brand_name: str = "HUGO RAMIREZ",
    tagline: str = "Design • Strategy • Immersive Systems",
    headline: str = "",
    subtitle: str = "",
) -> tuple:
    """
    Render a slide using Hugo's exact Canva design specifications.
    
    Returns: (output_path, filename)
    """
    
    specs = DESIGN_SYSTEM.get(preset_name, DESIGN_SYSTEM["carousel"])
    
    width = specs["width"]
    height = specs["height"]
    
    # Create base canvas
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    
    # Load and place main image
    with Image.open(image_path) as src:
        src = src.convert("RGBA")
        fitted = fit_cover(src, width, height)
        canvas.paste(fitted, (0, 0))
    
    # Create header gradient (top)
    header_gradient = create_gradient(
        width, 
        specs["header_height"],
        specs["header_gradient_color1"],
        specs["header_gradient_color2"]
    )
    canvas.alpha_composite(header_gradient, (0, 0))
    
    # Create footer gradient (bottom)
    footer_gradient = create_gradient(
        width,
        specs["footer_height"],
        specs["footer_gradient_color1"],
        specs["footer_gradient_color2"]
    )
    canvas.alpha_composite(footer_gradient, (0, specs["footer_start"]))
    
    # Draw text
    draw = ImageDraw.Draw(canvas)
    margin_left = specs["margin_left"]
    
    # === HEADER TEXT ===
    
    # Brand name (HUGO RAMIREZ) with letter spacing
    brand_font = load_font(specs["brand_font"], specs["brand_size"])
    brand_text = brand_name.upper()
    letter_spacing = specs.get("brand_letter_spacing", 3)
    
    draw_text_with_spacing(
        draw,
        (margin_left, specs["brand_y"]),
        brand_text,
        brand_font,
        specs["brand_color"],
        letter_spacing
    )
    
    # Tagline (right side of header)
    if tagline:
        tagline_font = load_font(specs["tagline_font"], specs["tagline_size"])
        tagline_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_width = tagline_bbox[2] - tagline_bbox[0]
        tagline_x = width - margin_left - tagline_width
        tagline_y = specs.get("tagline_y", specs["brand_y"])
        
        draw.text(
            (tagline_x, tagline_y),
            tagline,
            font=tagline_font,
            fill=specs["tagline_color"]
        )
    
    # === FOOTER TEXT ===
    
    # Title/Headline
    if headline:
        title_font = load_font(specs["title_font"], specs["title_size"])
        draw.text(
            (margin_left, specs["title_y"]),
            headline,
            font=title_font,
            fill=specs["title_color"]
        )
    
    # Subtitle with transparency support
    if subtitle:
        subtitle_font = load_font(specs["subtitle_font"], specs["subtitle_size"])
        subtitle_color = specs["subtitle_color"]
        
        # Create separate layer for alpha blending
        if len(subtitle_color) == 4 and subtitle_color[3] < 255:
            subtitle_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            subtitle_draw = ImageDraw.Draw(subtitle_layer)
            subtitle_draw.text(
                (margin_left, specs["subtitle_y"]),
                subtitle,
                font=subtitle_font,
                fill=subtitle_color
            )
            canvas.alpha_composite(subtitle_layer)
        else:
            # Direct draw for fully opaque
            fill_color = subtitle_color[:3] if len(subtitle_color) == 4 else subtitle_color
            draw.text(
                (margin_left, specs["subtitle_y"]),
                subtitle,
                font=subtitle_font,
                fill=fill_color
            )
    
    # Save output
    filename = f"slide_{uuid.uuid4().hex}.png"
    output_path = os.path.join(POST_OUTPUT_DIR, filename)
    canvas.convert("RGB").save(output_path, format="PNG", quality=95)
    
    print(f"✅ Generated: {filename}")
    
    return output_path, filename


# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route("/")
def home():
    return jsonify({
        "service": "Hugo Brand Engine",
        "version": "2.3 - All Fixes Applied",
        "status": "running",
        "fonts_loaded": {
            "extrabold": os.path.isfile(FONT_EXTRABOLD_PATH) if FONT_EXTRABOLD_PATH else False,
            "bold": os.path.isfile(FONT_BOLD_PATH) if FONT_BOLD_PATH else False,
            "semibold": os.path.isfile(FONT_SEMIBOLD_PATH) if FONT_SEMIBOLD_PATH else False,
            "medium": os.path.isfile(FONT_MEDIUM_PATH) if FONT_MEDIUM_PATH else False,
            "regular": os.path.isfile(FONT_REGULAR_PATH) if FONT_REGULAR_PATH else False,
            "light": os.path.isfile(FONT_LIGHT_PATH) if FONT_LIGHT_PATH else False,
        },
        "design_system": {
            "canvas": "1080x1350",
            "header": "108px, 10% gradient",
            "footer": "183px, 30% gradient",
            "brand_size": DESIGN_SYSTEM["carousel"]["brand_size"],
            "title_size": DESIGN_SYSTEM["carousel"]["title_size"],
        },
        "endpoints": {
            "health": "/health",
            "render_slide": "POST /render-slide"
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": "2.3"})


@app.route("/post_output/<filename>")
def serve_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)


@app.route("/render-slide", methods=["POST"])
def render_slide_endpoint():
    """
    Render a slide with Hugo's exact Canva design specifications.
    """
    try:
        payload = request.get_json(force=True)
    except:
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Get image
    image_path = None
    temp_file = None
    
    if payload.get("image_base64"):
        try:
            img_data = base64.b64decode(payload["image_base64"])
            temp_file = os.path.join(POST_IMAGE_DIR, f"temp_{uuid.uuid4().hex}.png")
            with open(temp_file, "wb") as f:
                f.write(img_data)
            image_path = temp_file
        except Exception as e:
            return jsonify({"error": f"Failed to decode base64: {str(e)}"}), 400
    
    elif payload.get("image_url"):
        try:
            response = requests.get(payload["image_url"], timeout=60)
            response.raise_for_status()
            temp_file = os.path.join(POST_IMAGE_DIR, f"temp_{uuid.uuid4().hex}.png")
            with open(temp_file, "wb") as f:
                f.write(response.content)
            image_path = temp_file
        except Exception as e:
            return jsonify({"error": f"Failed to download image: {str(e)}"}), 400
    
    else:
        return jsonify({"error": "No image_url or image_base64 provided"}), 400
    
    # Get parameters
    preset = payload.get("preset", "carousel")
    brand_name = payload.get("brand_name", "HUGO RAMIREZ")
    tagline = payload.get("tagline", "Design • Strategy • Immersive Systems")
    headline = payload.get("headline", "")
    
    # Handle bullets or subtitle
    subtitle = payload.get("subtitle", "")
    if not subtitle and payload.get("bullets"):
        bullets = payload["bullets"]
        if isinstance(bullets, list) and len(bullets) > 0:
            subtitle = bullets[0]
    
    # Render
    try:
        output_path, filename = render_slide_v2(
            image_path=image_path,
            preset_name=preset,
            brand_name=brand_name,
            tagline=tagline,
            headline=headline,
            subtitle=subtitle,
        )
        
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        
        base_url = request.host_url.rstrip('/')
        download_url = f"{base_url}/post_output/{filename}"
        
        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": download_url,
            "png_url": download_url,
        })
        
    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return jsonify({"error": str(e)}), 500


@app.route("/generate-post", methods=["POST"])
def generate_post_legacy():
    """Legacy endpoint - deprecated"""
    return jsonify({"error": "Use /render-slide instead"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting on port {port}")
    print(f"📁 Base dir: {BASE_DIR}")
    print(f"📁 Fonts check:")
    print(f"   - ExtraBold: {os.path.isfile(FONT_EXTRABOLD_PATH) if FONT_EXTRABOLD_PATH else 'NOT SET'}")
    print(f"   - Bold: {os.path.isfile(FONT_BOLD_PATH) if FONT_BOLD_PATH else 'NOT SET'}")
    print(f"   - SemiBold: {os.path.isfile(FONT_SEMIBOLD_PATH) if FONT_SEMIBOLD_PATH else 'NOT SET'}")
    print(f"   - Medium: {os.path.isfile(FONT_MEDIUM_PATH) if FONT_MEDIUM_PATH else 'NOT SET'}")
    print(f"   - Regular: {os.path.isfile(FONT_REGULAR_PATH) if FONT_REGULAR_PATH else 'NOT SET'}")
    print(f"   - Light: {os.path.isfile(FONT_LIGHT_PATH) if FONT_LIGHT_PATH else 'NOT SET'}")
    app.run(host="0.0.0.0", port=port, debug=False)
