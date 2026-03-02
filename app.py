from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import sys
import base64
from io import BytesIO
from urllib.parse import urlparse

print("🧠 Hugo Brand Engine v2.2 - Con Fallback a Fuentes de Sistema")

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

# Fonts: Inter custom primero, fallback a DejaVu de sistema (Ubuntu/Railway)
SYSTEM_FONTS = {
    "extrabold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Usa Bold como approx
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "semibold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Approx con Bold
    "medium": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Regular como approx
    "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "light": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Regular como approx
}

FONT_EXTRABOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'fonts', 'Inter-ExtraBold.ttf'),
    os.path.join(BASE_DIR, 'Inter-ExtraBold.ttf'),
    SYSTEM_FONTS["extrabold"]
)
FONT_BOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'fonts', 'Inter-Bold.ttf'),
    os.path.join(BASE_DIR, 'Inter-Bold.ttf'),
    SYSTEM_FONTS["bold"]
)
FONT_SEMIBOLD_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'fonts', 'Inter-SemiBold.ttf'),
    os.path.join(BASE_DIR, 'Inter-SemiBold.ttf'),
    SYSTEM_FONTS["semibold"]
)
FONT_MEDIUM_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'fonts', 'Inter-Medium.ttf'),
    os.path.join(BASE_DIR, 'Inter-Medium.ttf'),
    SYSTEM_FONTS["medium"]
)
FONT_REGULAR_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'fonts', 'Inter-Regular.ttf'),
    os.path.join(BASE_DIR, 'Inter-Regular.ttf'),
    SYSTEM_FONTS["regular"]
)
FONT_LIGHT_PATH = pick_existing_path(
    os.path.join(BASE_DIR, 'fonts', 'Inter-Light.ttf'),
    os.path.join(BASE_DIR, 'Inter-Light.ttf'),
    SYSTEM_FONTS["light"]
)

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# =============================================================================
# HUGO RAMIREZ - LINKEDIN CAROUSEL DESIGN SYSTEM
# =============================================================================
DESIGN_SYSTEM = {
    "carousel": {
        "width": 1080,
        "height": 1350,
        "header_height": 108,
        "header_gradient_color1": (0, 0, 0, 0),
        "header_gradient_color2": (0, 0, 0, 25),
        "footer_start": 1167,
        "footer_height": 183,
        "footer_gradient_color1": (0, 0, 0, 0),
        "footer_gradient_color2": (0, 0, 0, 77),
        "margin_left": 108,
        "margin_right": 108,
        "content_width": 864,
        "brand_font": "extrabold",
        "brand_size": 48,
        "brand_letter_spacing": 2,
        "brand_y": 35,
        "brand_color": (255, 255, 255),
        "tagline_font": "regular",
        "tagline_size": 42,
        "tagline_y": 42,
        "tagline_color": (255, 255, 255),
        "title_font": "semibold",
        "title_size": 42,
        "title_y": 1200,
        "title_color": (255, 255, 255),
        "subtitle_font": "light",
        "subtitle_size": 36,
        "subtitle_y": 1260,
        "subtitle_color": (255, 255, 255, 220),
    }
}
DESIGN_SYSTEM["linkedin"] = DESIGN_SYSTEM["carousel"]
DESIGN_SYSTEM["square"] = {
    **DESIGN_SYSTEM["carousel"],
    "width": 1080,
    "height": 1080,
    "footer_start": 897,
    "title_y": 933,
    "subtitle_y": 988,
}

def load_font(font_type: str, size: int):
    font_paths = {
        "extrabold": FONT_EXTRABOLD_PATH,
        "bold": FONT_BOLD_PATH,
        "semibold": FONT_SEMIBOLD_PATH,
        "medium": FONT_MEDIUM_PATH,
        "regular": FONT_REGULAR_PATH,
        "light": FONT_LIGHT_PATH,
    }
    
    path = font_paths.get(font_type, FONT_MEDIUM_PATH)
    
    print(f"Intentando cargar fuente {font_type} desde: {path}")
    if os.path.isfile(path):
        print(f"✅ Fuente {font_type} encontrada en {path}")
        try:
            return ImageFont.truetype(path, size)
        except Exception as e:
            print(f"❌ Error cargando {font_type}: {e} - fallback a sistema")
    else:
        print(f"❌ Fuente {font_type} NO encontrada en {path} - fallback a sistema")
    
    # Fallback final a default PIL si todo falla
    return ImageFont.load_default()

# Resto del código igual...
def create_gradient(width: int, height: int, color1: tuple, color2: tuple, direction: int = 180) -> Image.Image:
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
    img_w, img_h = img.size
    scale = max(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
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
    specs = DESIGN_SYSTEM.get(preset_name, DESIGN_SYSTEM["carousel"])
    width = specs["width"]
    height = specs["height"]
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    
    with Image.open(image_path) as src:
        src = src.convert("RGBA")
        fitted = fit_cover(src, width, height)
        canvas.paste(fitted, (0, 0))
    
    header_gradient = create_gradient(width, specs["header_height"], specs["header_gradient_color1"], specs["header_gradient_color2"])
    canvas.alpha_composite(header_gradient, (0, 0))
    
    footer_gradient = create_gradient(width, specs["footer_height"], specs["footer_gradient_color1"], specs["footer_gradient_color2"])
    canvas.alpha_composite(footer_gradient, (0, specs["footer_start"]))
    
    draw = ImageDraw.Draw(canvas)
    margin_left = specs["margin_left"]
    
    # Brand name con espaciado
    brand_font = load_font(specs["brand_font"], specs["brand_size"])
    brand_text = brand_name.upper()
    letter_spacing = specs["brand_letter_spacing"]
    x = margin_left
    for char in brand_text:
        if char != ' ':
            draw.text((x, specs["brand_y"]), char, font=brand_font, fill=specs["brand_color"])
            x += brand_font.getbbox(char)[2] + letter_spacing
        else:
            x += brand_font.getbbox(' ')[2]
    
    # Tagline
    if tagline:
        tagline_font = load_font(specs["tagline_font"], specs["tagline_size"])
        tagline_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_width = tagline_bbox[2] - tagline_bbox[0]
        tagline_x = width - margin_left - tagline_width
        tagline_y = specs.get("tagline_y", specs["brand_y"])
        draw.text((tagline_x, tagline_y), tagline, font=tagline_font, fill=specs["tagline_color"])
    
    # Headline
    if headline:
        title_font = load_font(specs["title_font"], specs["title_size"])
        draw.text((margin_left, specs["title_y"]), headline, font=title_font, fill=specs["title_color"])
    
    # Subtitle con transparencia
    if subtitle:
        subtitle_font = load_font(specs["subtitle_font"], specs["subtitle_size"])
        subtitle_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        subtitle_draw = ImageDraw.Draw(subtitle_layer)
        subtitle_draw.text((margin_left, specs["subtitle_y"]), subtitle, font=subtitle_font, fill=specs["subtitle_color"])
        try:
            canvas.alpha_composite(subtitle_layer, (0, 0))
        except Exception as e:
            print(f"Error en transparencia: {e} - usando sin alpha")
            draw.text((margin_left, specs["subtitle_y"]), subtitle, font=subtitle_font, fill=(255, 255, 255))
    
    filename = f"slide_{uuid.uuid4().hex}.png"
    output_path = os.path.join(POST_OUTPUT_DIR, filename)
    canvas.convert("RGB").save(output_path, format="PNG", quality=95)
    print(f"✅ Generated: {filename}")
    
    return output_path, filename

@app.route("/")
def home():
    return jsonify({"service": "Hugo Brand Engine", "version": "2.2 - Con System Fonts", "status": "running"})

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": "2.2"})

@app.route("/post_output/<filename>")
def serve_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

@app.route("/render-slide", methods=["POST"])
def render_slide_endpoint():
    try:
        payload = request.get_json(force=True)
    except:
        return jsonify({"error": "Invalid JSON"}), 400
    
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
    
    preset = payload.get("preset", "carousel")
    brand_name = payload.get("brand_name", "HUGO RAMIREZ")
    tagline = payload.get("tagline", "Design • Strategy • Immersive Systems")
    headline = payload.get("headline", "")
    subtitle = payload.get("subtitle", "")
    if not subtitle and payload.get("bullets"):
        bullets = payload["bullets"]
        if isinstance(bullets, list) and len(bullets) > 0:
            subtitle = bullets[0]
    
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
        })
    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
