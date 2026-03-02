# v3.3 text wrapping + softer subtitle
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
# Storage for generated images
# =========================
generated_images = {}

# =========================
# Paths
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# =========================
# Font Configuration
# =========================
FONT_BOLD_PATH = "Montserrat-Bold.ttf"

# =========================
# Colors
# =========================
WHITE = (255, 255, 255)
SUBTITLE_COLOR = (220, 220, 220)  # Lighter gray - less visual weight

# =========================
# Text Control Variables
# =========================
TITLE_MAX_WIDTH = 980       # Max pixels width for title
TITLE_MAX_LINES = 2         # Max lines for title
SUBTITLE_MAX_WIDTH = 980    # Max pixels width for subtitle
SUBTITLE_MAX_LINES = 2      # Max lines for subtitle

# =========================
# Load Fonts AT STARTUP
# =========================
try:
    brand_font = ImageFont.truetype(FONT_BOLD_PATH, 42)
    print(f"✅ brand_font loaded at 42px")
except Exception as e:
    print(f"❌ brand_font error: {e}")
    brand_font = ImageFont.load_default()

try:
    tagline_font = ImageFont.truetype(FONT_BOLD_PATH, 26)
    print(f"✅ tagline_font loaded at 26px")
except Exception as e:
    print(f"❌ tagline_font error: {e}")
    tagline_font = ImageFont.load_default()

try:
    title_font = ImageFont.truetype(FONT_BOLD_PATH, 40)
    print(f"✅ title_font loaded at 40px")
except Exception as e:
    print(f"❌ title_font error: {e}")
    title_font = ImageFont.load_default()

try:
    subtitle_font = ImageFont.truetype(FONT_BOLD_PATH, 28)  # Smaller than before
    print(f"✅ subtitle_font loaded at 28px")
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
TAGLINE_Y = 40
TITLE_Y = 1180              # Moved up slightly to allow for 2 lines
SUBTITLE_Y = 1230           # Will be calculated dynamically
LINE_SPACING = 8            # Space between lines
HEADER_HEIGHT = 150
FOOTER_HEIGHT = 280         # Increased for multi-line text


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
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def create_gradient_top_dark(width, height, alpha_max):
    """Create gradient: DARK at TOP, fades to transparent"""
    gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for y in range(height):
        alpha = int(alpha_max * (1 - y / height))
        for x in range(width):
            gradient.putpixel((x, y), (0, 0, 0, alpha))
    return gradient


def create_gradient_bottom_dark(width, height, alpha_max):
    """Create gradient: transparent to DARK at BOTTOM"""
    gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for y in range(height):
        alpha = int(alpha_max * (y / height))
        for x in range(width):
            gradient.putpixel((x, y), (0, 0, 0, alpha))
    return gradient


def wrap_text(text, font, max_width, draw):
    """
    Wrap text to fit within max_width.
    Returns list of lines.
    """
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        # Test if adding this word exceeds max width
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            # Save current line and start new one
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    # Don't forget the last line
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def truncate_lines(lines, max_lines, font, max_width, draw):
    """
    Truncate to max_lines. If truncated, add '...' to last line.
    """
    if len(lines) <= max_lines:
        return lines
    
    # Take only max_lines
    truncated = lines[:max_lines]
    
    # Add '...' to last line if it fits, otherwise truncate last line
    last_line = truncated[-1]
    while True:
        test_line = last_line + '...'
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            truncated[-1] = test_line
            break
        else:
            # Remove last word and try again
            words = last_line.split()
            if len(words) <= 1:
                truncated[-1] = '...'
                break
            last_line = ' '.join(words[:-1])
    
    return truncated


def render_slide(image_source, brand_name="HUGO RAMIREZ", tagline="Design • Strategy • Immersive Systems", headline="", subtitle=""):
    """Render slide with Hugo branding"""
    
    # Create canvas
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    
    # Load image
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
    header_gradient = create_gradient_top_dark(CANVAS_WIDTH, HEADER_HEIGHT, 150)
    canvas.alpha_composite(header_gradient, (0, 0))
    
    # Add footer gradient
    footer_gradient = create_gradient_bottom_dark(CANVAS_WIDTH, FOOTER_HEIGHT, 220)
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
    
    # === TITLE with wrapping ===
    title_y = TITLE_Y
    if headline:
        # Wrap and truncate title
        title_lines = wrap_text(headline, title_font, TITLE_MAX_WIDTH, draw)
        title_lines = truncate_lines(title_lines, TITLE_MAX_LINES, title_font, TITLE_MAX_WIDTH, draw)
        
        # Get line height
        bbox = draw.textbbox((0, 0), "Hg", font=title_font)
        title_line_height = bbox[3] - bbox[1] + LINE_SPACING
        
        # Draw each line
        for i, line in enumerate(title_lines):
            draw.text(
                (MARGIN_LEFT, title_y + (i * title_line_height)),
                line,
                font=title_font,
                fill=WHITE
            )
        
        # Calculate where subtitle starts (after title lines)
        subtitle_start_y = title_y + (len(title_lines) * title_line_height) + 10
    else:
        subtitle_start_y = SUBTITLE_Y
    
    # === SUBTITLE with wrapping ===
    if subtitle:
        # Wrap and truncate subtitle
        subtitle_lines = wrap_text(subtitle, subtitle_font, SUBTITLE_MAX_WIDTH, draw)
        subtitle_lines = truncate_lines(subtitle_lines, SUBTITLE_MAX_LINES, subtitle_font, SUBTITLE_MAX_WIDTH, draw)
        
        # Get line height
        bbox = draw.textbbox((0, 0), "Hg", font=subtitle_font)
        subtitle_line_height = bbox[3] - bbox[1] + LINE_SPACING
        
        # Draw each line with softer color
        for i, line in enumerate(subtitle_lines):
            draw.text(
                (MARGIN_LEFT, subtitle_start_y + (i * subtitle_line_height)),
                line,
                font=subtitle_font,
                fill=SUBTITLE_COLOR  # Softer gray
            )
    
    return canvas


# =========================
# ROUTES
# =========================

@app.route('/')
def home():
    return jsonify({
        "service": "Hugo Brand Engine",
        "version": "3.3",
        "status": "running",
        "features": ["text_wrapping", "auto_truncate", "softer_subtitle"],
        "fonts": {
            "Montserrat-Bold": os.path.isfile(FONT_BOLD_PATH),
        },
        "images_in_cache": len(generated_images)
    })


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': '3.3',
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
        
        # Get image
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
        
        # Save to file
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
    """Legacy endpoint"""
    return render_slide_endpoint()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Hugo Brand Engine v3.3 starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
