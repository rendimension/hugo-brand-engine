from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import base64

print("🧠 Hugo Brand Engine v2.5 - TEXT ONLY TEST")

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_IMAGE_DIR = os.path.join(BASE_DIR, 'post_image')
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# System font
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_font(size):
    """Get font at specified size"""
    try:
        font = ImageFont.truetype(FONT_PATH, size)
        print(f"✅ Font loaded at size {size}")
        return font
    except Exception as e:
        print(f"❌ Font error: {e}")
        return ImageFont.load_default()


def fit_cover(img, target_w, target_h):
    img_w, img_h = img.size
    scale = max(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def render_slide(image_path, brand_name="HUGO RAMIREZ", tagline="Design • Strategy • Immersive Systems", headline="", subtitle=""):
    """
    MINIMAL VERSION - Just image + text, NO gradients
    """
    
    width = 1080
    height = 1350
    
    # Create canvas with image
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    
    with Image.open(image_path) as src:
        src = src.convert("RGBA")
        fitted = fit_cover(src, width, height)
        canvas.paste(fitted, (0, 0))
    
    draw = ImageDraw.Draw(canvas)
    
    # ============================================
    # ONLY TEXT - NO GRADIENTS
    # ============================================
    
    # Brand name - TOP LEFT - SIZE 60
    brand_font = get_font(60)
    draw.text(
        (50, 30),
        brand_name.upper(),
        font=brand_font,
        fill=(255, 255, 255)
    )
    
    # Tagline - TOP RIGHT - SIZE 28
    tagline_font = get_font(28)
    bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tagline_w = bbox[2] - bbox[0]
    draw.text(
        (width - 50 - tagline_w, 45),
        tagline,
        font=tagline_font,
        fill=(255, 255, 255)
    )
    
    # Headline - BOTTOM - SIZE 52
    if headline:
        title_font = get_font(52)
        draw.text(
            (50, height - 150),
            headline,
            font=title_font,
            fill=(255, 255, 255)
        )
    
    # Subtitle - BOTTOM - SIZE 38
    if subtitle:
        sub_font = get_font(38)
        draw.text(
            (50, height - 80),
            subtitle,
            font=sub_font,
            fill=(255, 255, 255)
        )
    
    # Save
    filename = f"slide_{uuid.uuid4().hex}.png"
    output_path = os.path.join(POST_OUTPUT_DIR, filename)
    canvas.convert("RGB").save(output_path, format="PNG", quality=95)
    
    print(f"✅ Generated: {filename}")
    return output_path, filename


@app.route("/")
def home():
    font_exists = os.path.isfile(FONT_PATH)
    return jsonify({
        "service": "Hugo Brand Engine",
        "version": "2.5 - TEXT ONLY TEST",
        "font_path": FONT_PATH,
        "font_exists": font_exists,
        "sizes": {
            "brand": 60,
            "tagline": 28,
            "title": 52,
            "subtitle": 38
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": "2.5"})


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
    
    brand = payload.get("brand_name", "HUGO RAMIREZ")
    tagline = payload.get("tagline", "Design • Strategy • Immersive Systems")
    headline = payload.get("headline", "")
    
    subtitle = payload.get("subtitle", "")
    if not subtitle and payload.get("bullets"):
        bullets = payload["bullets"]
        if isinstance(bullets, list) and bullets:
            subtitle = bullets[0]
    
    try:
        output_path, filename = render_slide(
            image_path=image_path,
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
    print(f"🚀 Starting v2.5 TEXT ONLY on port {port}")
    print(f"📁 Font exists: {os.path.isfile(FONT_PATH)}")
    app.run(host="0.0.0.0", port=port, debug=False)
