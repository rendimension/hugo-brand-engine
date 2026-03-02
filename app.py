from flask import Flask, request, send_file, jsonify, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import io
import os
import base64
import uuid
import time
import requests

app = Flask(__name__)

# =========================
# Storage for generated images (in-memory, temporary)
# =========================
generated_images = {}

# =========================
# Paths
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# =========================
# Font Configuration - SAME AS PRESTIGE
# =========================
FONT_BOLD_PATH = "Montserrat-Bold.ttf"
FONT_REGULAR_PATH = "Montserrat-VariableFont_wght.ttf"

# =========================
# Colors
# =========================
WHITE = (255, 255, 255)

# =========================
# Font Sizes
# =========================
BRAND_FONT_SIZE = 42
TAGLINE_FONT_SIZE = 38
TITLE_FONT_SIZE = 40
SUBTITLE_FONT_SIZE = 42

# =========================
# Load Fonts AT STARTUP (exactly like Prestige)
# =========================
try:
    brand_font = ImageFont.truetype(FONT_BOLD_PATH, BRAND_FONT_SIZE)
    print(f"✅ brand_font loaded at {BRAND_FONT_SIZE}px")
except Exception as e:
    print(f"❌ brand_font error: {e}")
    brand_font = ImageFont.load_default()

try:
    tagline_font = ImageFont.truetype(FONT_REGULAR_PATH, TAGLINE_FONT_SIZE)
    print(f"✅ tagline_font loaded at {TAGLINE_FONT_SIZE}px")
except Exception as e:
    print(f"❌ tagline_font error: {e}")
    tagline_font = ImageFont.load_default()

try:
    title_font = ImageFont.truetype(FONT_BOLD_PATH, TITLE_FONT_SIZE)
    print(f"✅ title_font loaded at {TITLE_FONT_SIZE}px")
except Exception as e:
    print(f"❌ title_font error: {e}")
    title_font = ImageFont.load_default()

try:
    subtitle_font = ImageFont.truetype(FONT_REGULAR_PATH, SUBTITLE_FONT_SIZE)
    print(f"✅ subtitle_font loaded at {SUBTITLE_FONT_SIZE}px")
except Exception as e:
    print(f"❌ subtitle_font error: {e}")
    subtitle_font = ImageFont.load_default()

# =========================
# Layout Configuration
# =========================
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
MARGIN_LEFT = 50
MARGIN_RIGHT = 50
BRAND_Y = 35
TAGLINE_Y = 30
TITLE_Y = 1195
SUBTITLE_Y = 1260
HEADER_HEIGHT = 120
FOOTER_HEIGHT = 250


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
    """Scale and crop to fill (like CSS object-fit: cover)"""
    img_w, img_h = img.size
    scale = max(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
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
    """Render slide with Hugo branding"""
    
    # Create canvas
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    
    # Load image from various sources
    if isinstance(image_source, Image.Image):
        photo = image_source
    elif isinstance(image_source, bytes):
        photo = Image.open(io.BytesIO(image_source))
    elif isinstance(image_source, str) and os.path.exists(image_source):
        photo = Image.open(image_source)
    else:
        raise ValueError("Invalid image source")
    
    photo = photo.convert("RGBA")
    fitted = fit_cover(photo, CANVAS_WIDTH, CANVAS_HEIGHT)
    canvas.paste(fitted, (0, 0))
    
    # Add header gradient
    header_gradient = create_gradient(CANVAS_WIDTH, HEADER_HEIGHT, 0, 120)
    canvas.alpha_composite(header_gradient, (0, 0))
    
    # Add footer gradient
    footer_gradient = create_gradient(CANVAS_WIDTH, FOOTER_HEIGHT, 0, 180)
    canvas.alpha_composite(footer_gradient, (0, CANVAS_HEIGHT - FOOTER_HEIGHT))
    
    # Draw text
    draw = ImageDraw.Draw(canvas)
    
    # Brand name (top left)
    draw.text(
        (MARGIN_LEFT, BRAND_Y),
        brand_name.upper(),
        font=brand_font,
        fill=WHITE
    )
    
    # Tagline (top right)
    if tagline:
        bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_w = bbox[2] - bbox[0]
        draw.text(
            (CANVAS_WIDTH - MARGIN_RIGHT - tagline_w, TAGLINE_Y),
            tagline,
            font=tagline_font,
            fill=WHITE
        )
    
    # Headline (bottom)
    if headline:
        draw.text(
            (MARGIN_LEFT, TITLE_Y),
            headline,
            font=title_font,
            fill=WHITE
        )
    
    # Subtitle (bottom)
    if subtitle:
        draw.text(
            (MARGIN_LEFT, SUBTITLE_Y),
            subtitle,
            font=subtitle_font,
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
        "version": "3.0",
        "status": "running",
        "fonts": {
            "Montserrat-Bold": os.path.isfile(FONT_BOLD_PATH),
            "Montserrat-Variable": os.path.isfile(FONT_REGULAR_PATH),
        },
        "images_in_cache": len(generated_images)
    })


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': '3.0',
        'images_in_cache': len(generated_images)
    })


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
        
        data = request.get_json(force=True)
        
        # Get image from URL or base64
        image_source = None
        
        if data.get('image_base64'):
            image_data = base64.b64decode(data['image_base64'])
            image_source = Image.open(io.BytesIO(image_data))
        
        elif data.get('image_url'):
            resp = requests.get(data['image_url'], timeout=60)
            resp.raise_for_status()
            image_source = Image.open(io.BytesIO(resp.content))
        
        else:
            return jsonify({"error": "No image provided"}), 400
        
        # Get text params
        brand = data.get('brand_name', 'HUGO RAMIREZ')
        tagline = data.get('tagline', 'Design • Strategy • Immersive Systems')
        headline = data.get('headline', '')
        
        # Handle subtitle or bullets
        subtitle = data.get('subtitle', '')
        if not subtitle and data.get('bullets'):
            bullets = data['bullets']
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
        
        # Also save to file
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


@app.route('/generate-post', methods=['POST'])
def generate_post():
    """Legacy endpoint - redirects to render-slide"""
    return render_slide_endpoint()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Hugo Brand Engine v3.0 starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
