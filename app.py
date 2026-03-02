from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import sys
import base64
from io import BytesIO
from urllib.parse import urlparse

print("🧠 Hugo Brand Engine v2.2 - Canva Specs Corrected")

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
    FONT_MEDIUM_PATH,  # fallback
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
# Gradient colors from Canva: #A7A6DC (purple) to #000000 (black)
# =============================================================================

DESIGN_SYSTEM = {
    "carousel": {
        # Canvas
        "width": 1080,
        "height": 1350,
        
        # Header (Top gradient bar)
        # Canva: Linear gradient 180°, 10% opacity
        # Goes from transparent at top to dark at bottom
        "header_height": 108,  # 0px to 108px
        "header_gradient_color1": (0, 0, 0, 0),       # Top: fully transparent
        "header_gradient_color2": (0, 0, 0, 100),     # Bottom: subtle dark (10% feel)
        
        # Footer (Bottom gradient bar)
        # Canva: Linear gradient 180°, 30% opacity
        # Goes from transparent at top to dark at bottom
        "footer_start": 1167,  # starts at 1167px
        "footer_height": 183,  # 1167px to 1350px
        "footer_gradient_color1": (0, 0, 0, 0),       # Top: fully transparent
        "footer_gradient_color2": (0, 0, 0, 200),     # Bottom: darker (30% feel)
        
        # Content margins
        "margin_left": 108,
        "margin_right": 108,  # ends at 972px
        "content_width": 864,
        
        # Typography - Header
        # HUGO RAMIREZ: Inter ExtraBold, size 20 in Canva = ~60px at 1080p
        "brand_font": "extrabold",
        "brand_size": 92,              # Adjusted for visibility
        "brand_letter_spacing": 134,   # Canva units
        "brand_y": 35,                 # Centered in 108px header
        "brand_color": (255, 255, 255),
        
        # Tagline: Inter Regular, size 20.5 in Canva
        "tagline_font": "regular",
        "tagline_size": 85,            # Adjusted for visibility
        "tagline_y": 42,               # Aligned with brand
        "tagline_color": (255, 255, 255),
        
        # Typography - Footer
        # Title: Inter SemiBold, size 20 in Canva = ~48px at 1080p
        "title_font": "semibold",
        "title_size": 72,              # Good visibility
        "title_y": 1200,               # Position in footer
        "title_color": (255, 255, 255),
        
        # Subtitle: Inter Light, size 20 in Canva
        "subtitle_font": "light",
        "subtitle_size": 68,           # Slightly smaller than title
        "subtitle_y": 1260,            # Below title
        "subtitle_color": (255, 255, 255, 220),  # Slightly transparent
    }
}

# Also support these preset aliases
DESIGN_SYSTEM["linkedin"] = DESIGN_SYSTEM["carousel"]
DESIGN_SYSTEM["square"] = {
    **DESIGN_SYSTEM["carousel"],
    "width": 1080,
    "height": 1080,
    "footer_start": 897,  # adjusted for square
    "title_y": 933,
    "subtitle_y": 988,
}


def load_font(font_type: str, size: int):
    """Load font by type with fallback"""
    font_paths = {
        "extrabold": FONT_EXTRABOLD_PATH,
        "bold": FONT_BOLD_PATH,
        "semibold": FONT_SEMIBOLD_PATH,
        "medium": FONT_MEDIUM_PATH,
        "regular": FONT_REGULAR_PATH,
        "light": FONT_LIGHT_PATH,
    }
    
    path = font_paths.get(font_type, FONT_MEDIUM_PATH)
    
    try:
        if path and os.path.isfile(path):
            return ImageFont.truetype(path, size)
    except Exception as e:
        print(f"Font load error for {font_type}: {e}")
    
    # Fallback
    try:
        return ImageFont.truetype(FONT_BOLD_PATH, size)
    except:
        return ImageFont.load_default()


def create_gradient(width: int, height: int, color1: tuple, color2: tuple, direction: int = 180) -> Image.Image:
    """Create a gradient image. Direction 180 = top to bottom."""
    gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    for y in range(height):
        # Calculate interpolation factor
        factor = y / height if height > 0 else 0
        
        # Interpolate colors
        r = int(color1[0] + (color2[0] - color1[0]) * factor)
        g = int(color1[1] + (color2[1] - color1[1]) * factor)
        b = int(color1[2] + (color2[2] - color1[2]) * factor)
        a = int(color1[3] + (color2[3] - color1[3]) * factor)
        
        for x in range(width):
            gradient.putpixel((x, y), (r, g, b, a))
    
    return gradient


def fit_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale and crop image to fill target dimensions (like CSS object-fit: cover)"""
    img_w, img_h = img.size
    
    # Calculate scale to cover
    scale = max(target_w / img_w, target_h / img_h)
    
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Crop to center
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    
    return img.crop((left, top, left + target_w, top + target_h))


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
    
    # Get design specs
    specs = DESIGN_SYSTEM.get(preset_name, DESIGN_SYSTEM["carousel"])
    
    width = specs["width"]
    height = specs["height"]
    
    # Create base canvas
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    
    # Load and place main image (full canvas, will be covered by gradients)
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
    
    # Brand name (HUGO RAMIREZ)
    brand_font = load_font(specs["brand_font"], specs["brand_size"])
    brand_text = brand_name.upper()
    
    # Apply letter spacing visually by adding spaces
    if specs.get("brand_letter_spacing", 0) > 100:
        brand_text = ' '.join(brand_text)  # Add space between each char
    
    draw.text(
        (margin_left, specs["brand_y"]),
        brand_text,
        font=brand_font,
        fill=specs["brand_color"]
    )
    
    # Tagline (right side of header)
    if tagline:
        tagline_font = load_font(specs["tagline_font"], int(specs["tagline_size"]))
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
    
    # Headline/Title
    if headline:
        title_font = load_font(specs["title_font"], specs["title_size"])
        draw.text(
            (margin_left, specs["title_y"]),
            headline,
            font=title_font,
            fill=specs["title_color"]
        )
    
    # Subtitle
    if subtitle:
        subtitle_font = load_font(specs["subtitle_font"], specs["subtitle_size"])
        subtitle_color = specs["subtitle_color"]
        # Handle RGBA color
        if len(subtitle_color) == 4:
            subtitle_color = subtitle_color[:3]  # PIL text needs RGB
        draw.text(
            (margin_left, specs["subtitle_y"]),
            subtitle,
            font=subtitle_font,
            fill=subtitle_color
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
        "version": "2.2 - Canva Specs Corrected",
        "status": "running",
        "design_system": {
            "canvas": "1080x1350",
            "header": "108px gradient transparent->dark",
            "footer": "183px gradient transparent->dark",
            "margins": "108px left/right",
            "fonts": "Inter family",
            "brand_size": 48,
            "title_size": 42,
            "subtitle_size": 32
        },
        "endpoints": {
            "health": "/health",
            "render_slide": "POST /render-slide"
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": "2.2"})


@app.route("/post_output/<filename>")
def serve_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)


@app.route("/render-slide", methods=["POST"])
def render_slide_endpoint():
    """
    Render a slide with Hugo's exact Canva design specifications.
    
    Expected JSON:
    {
        "image_url": "https://...",  // OR
        "image_base64": "base64...",
        "preset": "carousel",  // or "linkedin", "square"
        "brand_name": "HUGO RAMIREZ",
        "tagline": "Design • Strategy • Immersive Systems",
        "headline": "Why 3D Renderings Aren't Always Better",
        "bullets": ["3D visuals look real. But..."]  // or "subtitle": "..."
    }
    """
    try:
        payload = request.get_json(force=True)
    except:
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Get image
    image_path = None
    temp_file = None
    
    if payload.get("image_base64"):
        # Decode base64
        try:
            img_data = base64.b64decode(payload["image_base64"])
            temp_file = os.path.join(POST_IMAGE_DIR, f"temp_{uuid.uuid4().hex}.png")
            with open(temp_file, "wb") as f:
                f.write(img_data)
            image_path = temp_file
        except Exception as e:
            return jsonify({"error": f"Failed to decode base64: {str(e)}"}), 400
    
    elif payload.get("image_url"):
        # Download image
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
            subtitle = bullets[0]  # Use first bullet as subtitle
    
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
        
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Return URLs
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


# =============================================================================
# LEGACY ENDPOINT (backwards compatible)
# =============================================================================

@app.route("/generate-post", methods=["POST"])
def generate_post_legacy():
    """Legacy endpoint for backwards compatibility"""
    return jsonify({"error": "Legacy endpoint deprecated. Use /render-slide instead."}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
