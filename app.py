from flask import Flask, request, send_file, jsonify, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import io
import os
import base64
import uuid
import time
import requests

app = Flask(__name__)

print("🧠 Hugo Brand Engine v2.6 - Prestige Pattern")

# =========================
# Paths
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_IMAGE_DIR = os.path.join(BASE_DIR, 'post_image')
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# =========================
# Storage for generated images
# =========================
generated_images = {}

# =========================
# Font Configuration - LOADED AT STARTUP (like Prestige)
# =========================
FONT_BOLD_PATH = os.path.join(BASE_DIR, "Inter-Bold.ttf")
FONT_SEMIBOLD_PATH = os.path.join(BASE_DIR, "Inter-SemiBold.ttf")
FONT_MEDIUM_PATH = os.path.join(BASE_DIR, "Inter-Medium.ttf")

# Fallback to system font if Inter not found
SYSTEM_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# =========================
# Font Sizes
# =========================
BRAND_FONT_SIZE = 42
TAGLINE_FONT_SIZE = 22
TITLE_FONT_SIZE = 40
SUBTITLE_FONT_SIZE = 32

# =========================
# Load Fonts AT STARTUP (key difference!)
# =========================
def load_font_safe(path, size, fallback_path=None):
    """Load font with fallback"""
    try:
        if os.path.isfile(path):
            print(f"✅ Loading font: {path} at size {size}")
            return ImageFont.truetype(path, size)
    except Exception as e:
        print(f"❌ Error loading {path}: {e}")
    
    # Try fallback
    if fallback_path and os.path.isfile(fallback_path):
        try:
            print(f"⚠️ Using fallback: {fallback_path}")
            return ImageFont.truetype(fallback_path, size)
        except:
            pass
    
    print(f"⚠️ Using default font for size {size}")
    return ImageFont.load_default()

# LOAD ALL FONTS NOW (not in functions)
brand_font = load_font_safe(FONT_BOLD_PATH, BRAND_FONT_SIZE, SYSTEM_FONT)
tagline_font = load_font_safe(FONT_MEDIUM_PATH, TAGLINE_FONT_SIZE, SYSTEM_FONT)
title_font = load_font_safe(FONT_SEMIBOLD_PATH, TITLE_FONT_SIZE, SYSTEM_FONT)
subtitle_font = load_font_safe(FONT_MEDIUM_PATH, SUBTITLE_FONT_SIZE, SYSTEM_FONT)

print(f"📁 Fonts loaded:")
print(f"   - brand_font: {brand_font}")
print(f"   - tagline_font: {tagline_font}")
print(f"   - title_font: {title_font}")
print(f"   - subtitle_font: {subtitle_font}")

# =========================
# Colors
# =========================
WHITE = (255, 255, 255)

# =========================
# Layout Configuration
# =========================
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
MARGIN_LEFT = 50
MARGIN_RIGHT = 50

# Header
BRAND_Y = 35
TAGLINE_Y = 42

# Footer
TITLE_Y = 1195
SUBTITLE_Y = 1260

# Gradients
HEADER_HEIGHT = 120
FOOTER_HEIGHT = 200


def cleanup_old_images():
    """Remove images older than 10 minutes"""
    current_time = time.time()
    keys_to_delete = []
    for key, value in generated_images.items():
        if current_time - value['timestamp'] > 600:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del generated_images[key]


def fit_cover(img, target_w, target_h):
    """Scale and crop to fill"""
    img_w, img_h = img.size
    scale = max(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def create_gradient(width, height, alpha_start, alpha_end):
    """Create vertical gradient overlay"""
    gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for y in range(height):
        alpha = int(alpha_start + (alpha_end - alpha_start) * (y / height))
        for x in range(width):
            gradient.putpixel((x, y), (0, 0, 0, alpha))
    return gradient


def render_slide(image_source, brand_name="HUGO RAMIREZ", tagline="Design • Strategy • Immersive Systems", headline="", subtitle=""):
    """
    Render slide with branding - uses pre-loaded fonts
    """
    
    # Create canvas
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    
    # Load and place main image
    if isinstance(image_source, str):
        # It's a file path
        photo = Image.open(image_source)
    else:
        # It's already an Image
        photo = image_source
    
    photo = photo.convert("RGBA")
    fitted = fit_cover(photo, CANVAS_WIDTH, CANVAS_HEIGHT)
    canvas.paste(fitted, (0, 0))
    
    # Add header gradient (transparent to dark)
    header_gradient = create_gradient(CANVAS_WIDTH, HEADER_HEIGHT, 0, 60)
    canvas.alpha_composite(header_gradient, (0, 0))
    
    # Add footer gradient (transparent to dark)
    footer_gradient = create_gradient(CANVAS_WIDTH, FOOTER_HEIGHT, 0, 100)
    canvas.alpha_composite(footer_gradient, (0, CANVAS_HEIGHT - FOOTER_HEIGHT))
    
    # Draw text
    draw = ImageDraw.Draw(canvas)
    
    # === HEADER ===
    
    # Brand name (top left)
    draw.text(
        (MARGIN_LEFT, BRAND_Y),
        brand_name.upper(),
        font=brand_font,  # Pre-loaded font!
        fill=WHITE
    )
    
    # Tagline (top right)
    if tagline:
        bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_w = bbox[2] - bbox[0]
        draw.text(
            (CANVAS_WIDTH - MARGIN_RIGHT - tagline_w, TAGLINE_Y),
            tagline,
            font=tagline_font,  # Pre-loaded font!
            fill=WHITE
        )
    
    # === FOOTER ===
    
    # Headline
    if headline:
        draw.text(
            (MARGIN_LEFT, TITLE_Y),
            headline,
            font=title_font,  # Pre-loaded font!
            fill=WHITE
        )
    
    # Subtitle
    if subtitle:
        draw.text(
            (MARGIN_LEFT, SUBTITLE_Y),
            subtitle,
            font=subtitle_font,  # Pre-loaded font!
            fill=WHITE
        )
    
    return canvas


# =========================
# ROUTES
# =========================

@app.route('/')
def home():
    return jsonify({
        "service": "Hugo Brand Engine",
        "version": "2.6 - Prestige Pattern",
        "status": "running",
        "fonts": {
            "Inter-Bold exists": os.path.isfile(FONT_BOLD_PATH),
            "Inter-SemiBold exists": os.path.isfile(FONT_SEMIBOLD_PATH),
            "Inter-Medium exists": os.path.isfile(FONT_MEDIUM_PATH),
            "System font exists": os.path.isfile(SYSTEM_FONT),
        },
        "sizes": {
            "brand": BRAND_FONT_SIZE,
            "tagline": TAGLINE_FONT_SIZE,
            "title": TITLE_FONT_SIZE,
            "subtitle": SUBTITLE_FONT_SIZE,
        },
        "images_in_cache": len(generated_images)
    })


@app.route('/health')
def health():
    return jsonify({"status": "healthy", "version": "2.6"})


@app.route('/post_output/<filename>')
def serve_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)


@app.route('/download/<image_id>')
def download_image(image_id):
    """Download generated image by ID"""
    try:
        if image_id not in generated_images:
            return jsonify({'error': 'Image not found or expired'}), 404
        
        image_data = generated_images[image_id]['data']
        img_buffer = io.BytesIO(image_data)
        img_buffer.seek(0)
        
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=False,
            download_name=f'hugo_{image_id}.png'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/render-slide', methods=['POST'])
def render_slide_endpoint():
    """Main endpoint for n8n"""
    try:
        cleanup_old_images()
        
        payload = request.get_json(force=True)
        
        # Get image
        image_source = None
        temp_file = None
        
        if payload.get('image_base64'):
            img_data = base64.b64decode(payload['image_base64'])
            image_source = Image.open(io.BytesIO(img_data))
        
        elif payload.get('image_url'):
            resp = requests.get(payload['image_url'], timeout=60)
            resp.raise_for_status()
            image_source = Image.open(io.BytesIO(resp.content))
        
        else:
            return jsonify({"error": "No image provided"}), 400
        
        # Get text params
        brand = payload.get('brand_name', 'HUGO RAMIREZ')
        tagline = payload.get('tagline', 'Design • Strategy • Immersive Systems')
        headline = payload.get('headline', '')
        
        subtitle = payload.get('subtitle', '')
        if not subtitle and payload.get('bullets'):
            bullets = payload['bullets']
            if isinstance(bullets, list) and bullets:
                subtitle = bullets[0]
        
        # Render
        img = render_slide(
            image_source=image_source,
            brand_name=brand,
            tagline=tagline,
            headline=headline,
            subtitle=subtitle,
        )
        
        # Save to buffer
        img_buffer = io.BytesIO()
        img.convert("RGB").save(img_buffer, format='PNG', quality=95)
        img_buffer.seek(0)
        
        # Store in cache
        image_id = str(uuid.uuid4())
        generated_images[image_id] = {
            'data': img_buffer.getvalue(),
            'timestamp': time.time()
        }
        
        # Also save to file (for /post_output/ route)
        filename = f"slide_{image_id}.png"
        output_path = os.path.join(POST_OUTPUT_DIR, filename)
        img.convert("RGB").save(output_path, format='PNG', quality=95)
        
        # Build URLs
        base_url = request.host_url.rstrip('/')
        
        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": f"{base_url}/download/{image_id}",
            "png_url": f"{base_url}/post_output/{filename}",
            "image_id": image_id
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


# Legacy endpoint
@app.route('/generate-post', methods=['POST'])
def generate_post():
    """Legacy endpoint - redirects to render-slide"""
    return render_slide_endpoint()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting v2.6 on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
