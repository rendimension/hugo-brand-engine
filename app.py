from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import sys
import base64
from io import BytesIO
from urllib.parse import urlparse

print("🧠 Hugo Brand Engine v2.4 - DejaVu System Fonts")

app = Flask(__name__)

# === Paths (Railway compatible) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

POST_IMAGE_DIR = os.path.join(BASE_DIR, 'post_image')
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# =============================================================================
# SYSTEM FONTS (Railway/Linux)
# =============================================================================
# Using DejaVu fonts that come preinstalled on Linux systems
# No need to upload .ttf files!
# =============================================================================

SYSTEM_FONTS = {
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "oblique": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
}

# Check which fonts exist
print("📁 System fonts check:")
for name, path in SYSTEM_FONTS.items():
    exists = os.path.isfile(path)
    print(f"   - {name}: {'✅' if exists else '❌'} {path}")


# =============================================================================
# HUGO RAMIREZ - LINKEDIN CAROUSEL DESIGN SYSTEM
# =============================================================================

DESIGN_SYSTEM = {
    "carousel": {
        # Canvas
        "width": 1080,
        "height": 1350,
        
        # Header gradient (10% opacity)
        "header_height": 108,
        "header_gradient_color1": (0, 0, 0, 0),
        "header_gradient_color2": (0, 0, 0, 25),
        
        # Footer gradient (30% opacity)
        "footer_start": 1167,
        "footer_height": 183,
        "footer_gradient_color1": (0, 0, 0, 0),
        "footer_gradient_color2": (0, 0, 0, 77),
        
        # Margins
        "margin_left": 108,
        "margin_right": 108,
        
        # Typography - Header
        "brand_size": 42,
        "brand_letter_spacing": 4,
        "brand_y": 38,
        "brand_color": (255, 255, 255),
        
        "tagline_size": 22,
        "tagline_y": 45,
        "tagline_color": (255, 255, 255),
        
        # Typography - Footer
        "title_size": 40,
        "title_y": 1195,
        "title_color": (255, 255, 255),
        
        "subtitle_size": 32,
        "subtitle_y": 1255,
        "subtitle_color": (255, 255, 255, 200),
    }
}

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


def load_system_font(style: str, size: int):
    """Load system font with fallback"""
    path = SYSTEM_FONTS.get(style, SYSTEM_FONTS["bold"])
    
    try:
        if os.path.isfile(path):
            font = ImageFont.truetype(path, size)
            print(f"✅ Loaded {style} at size {size}")
            return font
    except Exception as e:
        print(f"❌ Error loading {style}: {e}")
    
    # Fallback to any available system font
    for fallback_path in SYSTEM_FONTS.values():
        try:
            if os.path.isfile(fallback_path):
                return ImageFont.truetype(fallback_path, size)
        except:
            continue
    
    print("⚠️ Using PIL default font")
    return ImageFont.load_default()


def create_gradient(width: int, height: int, color1: tuple, color2: tuple) -> Image.Image:
    """Create vertical gradient"""
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
    """Scale and crop to fill"""
    img_w, img_h = img.size
    scale = max(target_w / img_w, target_h / img_h)
    
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    
    return img.crop((left, top, left + target_w, top + target_h))


def draw_text_with_spacing(draw, position, text, font, fill, spacing=0):
    """Draw text with letter spacing"""
    x, y = position
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        x += char_width + spacing


def render_slide(
    image_path: str,
    preset_name: str = "carousel",
    brand_name: str = "HUGO RAMIREZ",
    tagline: str = "Design • Strategy • Immersive Systems",
    headline: str = "",
    subtitle: str = "",
) -> tuple:
    """Render slide with system fonts"""
    
    specs = DESIGN_SYSTEM.get(preset_name, DESIGN_SYSTEM["carousel"])
    width = specs["width"]
    height = specs["height"]
    
    # Create canvas
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    
    # Load main image
    with Image.open(image_path) as src:
        src = src.convert("RGBA")
        fitted = fit_cover(src, width, height)
        canvas.paste(fitted, (0, 0))
    
    # Header gradient
    header = create_gradient(
        width, specs["header_height"],
        specs["header_gradient_color1"],
        specs["header_gradient_color2"]
    )
    canvas.alpha_composite(header, (0, 0))
    
    # Footer gradient
    footer = create_gradient(
        width, specs["footer_height"],
        specs["footer_gradient_color1"],
        specs["footer_gradient_color2"]
    )
    canvas.alpha_composite(footer, (0, specs["footer_start"]))
    
    # Draw text
    draw = ImageDraw.Draw(canvas)
    margin = specs["margin_left"]
    
    # === HEADER ===
    
    # Brand name
    brand_font = load_system_font("bold", specs["brand_size"])
    draw_text_with_spacing(
        draw,
        (margin, specs["brand_y"]),
        brand_name.upper(),
        brand_font,
        specs["brand_color"],
        specs["brand_letter_spacing"]
    )
    
    # Tagline
    if tagline:
        tagline_font = load_system_font("regular", specs["tagline_size"])
        bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_w = bbox[2] - bbox[0]
        tagline_x = width - margin - tagline_w
        
        draw.text(
            (tagline_x, specs["tagline_y"]),
            tagline,
            font=tagline_font,
            fill=specs["tagline_color"]
        )
    
    # === FOOTER ===
    
    # Title
    if headline:
        title_font = load_system_font("bold", specs["title_size"])
        draw.text(
            (margin, specs["title_y"]),
            headline,
            font=title_font,
            fill=specs["title_color"]
        )
    
    # Subtitle
    if subtitle:
        subtitle_font = load_system_font("regular", specs["subtitle_size"])
        sub_color = specs["subtitle_color"]
        
        if len(sub_color) == 4 and sub_color[3] < 255:
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            layer_draw = ImageDraw.Draw(layer)
            layer_draw.text(
                (margin, specs["subtitle_y"]),
                subtitle,
                font=subtitle_font,
                fill=sub_color
            )
            canvas.alpha_composite(layer)
        else:
            draw.text(
                (margin, specs["subtitle_y"]),
                subtitle,
                font=subtitle_font,
                fill=sub_color[:3] if len(sub_color) == 4 else sub_color
            )
    
    # Save
    filename = f"slide_{uuid.uuid4().hex}.png"
    output_path = os.path.join(POST_OUTPUT_DIR, filename)
    canvas.convert("RGB").save(output_path, format="PNG", quality=95)
    
    print(f"✅ Generated: {filename}")
    return output_path, filename


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def home():
    fonts_status = {name: os.path.isfile(path) for name, path in SYSTEM_FONTS.items()}
    return jsonify({
        "service": "Hugo Brand Engine",
        "version": "2.4 - DejaVu System Fonts",
        "status": "running",
        "fonts": fonts_status,
        "design": {
            "brand_size": DESIGN_SYSTEM["carousel"]["brand_size"],
            "title_size": DESIGN_SYSTEM["carousel"]["title_size"],
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": "2.4"})


@app.route("/post_output/<filename>")
def serve_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)


@app.route("/render-slide", methods=["POST"])
def render_slide_endpoint():
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
            return jsonify({"error": f"Base64 error: {e}"}), 400
    
    elif payload.get("image_url"):
        try:
            resp = requests.get(payload["image_url"], timeout=60)
            resp.raise_for_status()
            temp_file = os.path.join(POST_IMAGE_DIR, f"temp_{uuid.uuid4().hex}.png")
            with open(temp_file, "wb") as f:
                f.write(resp.content)
            image_path = temp_file
        except Exception as e:
            return jsonify({"error": f"Download error: {e}"}), 400
    else:
        return jsonify({"error": "No image provided"}), 400
    
    # Params
    preset = payload.get("preset", "carousel")
    brand = payload.get("brand_name", "HUGO RAMIREZ")
    tagline = payload.get("tagline", "Design • Strategy • Immersive Systems")
    headline = payload.get("headline", "")
    
    subtitle = payload.get("subtitle", "")
    if not subtitle and payload.get("bullets"):
        bullets = payload["bullets"]
        if isinstance(bullets, list) and bullets:
            subtitle = bullets[0]
    
    # Render
    try:
        output_path, filename = render_slide(
            image_path=image_path,
            preset_name=preset,
            brand_name=brand,
            tagline=tagline,
            headline=headline,
            subtitle=subtitle,
        )
        
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        
        base_url = request.host_url.rstrip('/')
        url = f"{base_url}/post_output/{filename}"
        
        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": url,
            "png_url": url,
        })
        
    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
