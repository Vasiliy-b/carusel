"""
Flask Web UI for Multi-Agent Content Generator
Simple interface for SMM team to trigger generations and browse results
Supports multi-session with SQLite job management.
"""
import os
import subprocess
import uuid
import glob
import zipfile
import re
import logging
import json
from datetime import datetime
from pathlib import Path
from io import BytesIO
from flask import Flask, render_template, jsonify, request, send_file
from werkzeug.utils import secure_filename
import threading

# Import SQLite job manager
from .job_db import job_db

# Setup logging for web UI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/web_ui.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
logger.info("Flask app initialized")

# Configure Flask for file uploads (up to 10 reference images)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max for multiple images
app.config['UPLOAD_FOLDER'] = Path(__file__).parent.parent / 'temp' / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Base paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "posts"

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Clean up stale jobs on startup (SQLite-based)
stale_count = job_db.cleanup_stale_jobs()
if stale_count > 0:
    logger.info(f"Cleaned up {stale_count} stale job(s) from previous run")


def scan_generated_posts():
    """Scan output directory for all generated posts"""
    posts = []
    
    if not OUTPUT_DIR.exists():
        return posts
    
    # Sort by modification time (newest first)
    post_dirs = sorted(OUTPUT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    
    for post_dir in post_dirs:
        if not post_dir.is_dir():
            continue
        
        post_id = post_dir.name
        md_file = post_dir / f"{post_id}_content.md"
        
        if not md_file.exists():
            continue
        
        # Read metadata from markdown file
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title (first line starting with #)
            title = "Untitled"
            for line in content.split('\n'):
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            
            # Get first image as thumbnail
            images_dir = post_dir / "images"
            thumbnail = None
            if images_dir.exists():
                image_files = sorted(images_dir.glob("slide_*.png"))
                if image_files:
                    thumbnail = f"/static/posts/{post_id}/images/{image_files[0].name}"
            
            # Extract date from markdown or folder name
            date_str = "Unknown"
            for line in content.split('\n'):
                if line.startswith('**Generated:**'):
                    date_str = line.split('**Generated:**')[1].strip()
                    break
            
            # Count images
            image_count = len(list(images_dir.glob("slide_*.png"))) if images_dir.exists() else 0
            
            posts.append({
                "post_id": post_id,
                "title": title,
                "date": date_str,
                "thumbnail": thumbnail,
                "image_count": image_count
            })
            
        except Exception as e:
            print(f"Error reading post {post_id}: {e}")
            continue
    
    return posts


def run_generator_async(job_id):
    """Run content generator in background (sheet mode)"""
    logger.info(f"BACKGROUND: Starting sheet mode generation for job {job_id}")

    try:
        # Set STYLE environment variable (empty by default - set in UI if needed)
        env = os.environ.copy()
        env['STYLE'] = os.environ.get('STYLE', '')  # Use current STYLE or empty

        # Use venv Python interpreter
        venv_python = BASE_DIR / ".venv" / "bin" / "python"
        if not venv_python.exists():
            logger.warning(f"BACKGROUND: venv not found at {venv_python}, using system python")
            venv_python = "python"
        else:
            venv_python = str(venv_python)
            logger.info(f"BACKGROUND: Using venv python: {venv_python}")

        logger.info(f"BACKGROUND: Running subprocess for sheet mode...")
        # Run generator with venv python and job_id for session isolation
        result = subprocess.run(
            [venv_python, '-m', 'content_generator.main', '--job-id', job_id],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            env=env
        )

        # Parse output to find generated post_id
        post_id = None
        for line in result.stdout.split('\n'):
            if 'post_' in line and 'Selected post:' in line:
                # Extract post_id from log line
                parts = line.split('post_')
                if len(parts) > 1:
                    post_id = 'post_' + parts[1].split()[0]
                    break

        logger.info(f"BACKGROUND: Subprocess completed with return code {result.returncode}")

        if result.returncode == 0:
            logger.info(f"BACKGROUND: Job {job_id} completed successfully. Post: {post_id}")
            job_db.complete_job(job_id, post_id)
        else:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            logger.error(f"BACKGROUND: Job {job_id} failed: {error_msg}")
            job_db.fail_job(job_id, error_msg)

    except Exception as e:
        logger.error(f"BACKGROUND: Exception in job {job_id}: {e}", exc_info=True)
        job_db.fail_job(job_id, str(e))


@app.route('/')
def index():
    """Homepage - Gallery view of all generated posts"""
    logger.info("INDEX: Loading homepage")
    posts = scan_generated_posts()
    logger.info(f"INDEX: Found {len(posts)} posts")

    # Get running jobs info (multi-session support)
    running_jobs = job_db.get_running_jobs()
    running_count = len(running_jobs)
    max_concurrent = job_db.MAX_CONCURRENT_JOBS

    # Get current STYLE setting (empty by default)
    current_style = os.environ.get('STYLE', '')

    return render_template('index.html',
                          posts=posts,
                          running_jobs=running_jobs,
                          running_count=running_count,
                          max_concurrent=max_concurrent,
                          current_style=current_style)


@app.route('/generate', methods=['POST'])
def generate():
    """Trigger new content generation (sheet mode)"""
    logger.info("GENERATE: Sheet mode generation triggered")

    job_id = str(uuid.uuid4())

    # Atomically create job if under concurrency limit
    if not job_db.create_job(job_id, input_mode='sheet'):
        running_count = job_db.get_running_count()
        logger.warning(f"GENERATE: At capacity ({running_count}/{job_db.MAX_CONCURRENT_JOBS})")
        return jsonify({
            "error": f"Max concurrent jobs ({job_db.MAX_CONCURRENT_JOBS}) reached. {running_count} running.",
            "running_count": running_count,
            "max_concurrent": job_db.MAX_CONCURRENT_JOBS
        }), 429  # Too Many Requests

    logger.info(f"GENERATE: Created job {job_id}")

    # Run in background thread
    thread = threading.Thread(target=run_generator_async, args=(job_id,))
    thread.daemon = True
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "running",
        "running_count": job_db.get_running_count(),
        "max_concurrent": job_db.MAX_CONCURRENT_JOBS
    })


@app.route('/generate_from_text', methods=['POST'])
def generate_from_text():
    """Generate content from free-form text input with optional reference images"""
    logger.info("GENERATE_TEXT: Text mode generation triggered")

    # Get text input first (validate before creating job)
    user_text = request.form.get('text_input', '').strip()
    if not user_text:
        logger.error("GENERATE_TEXT: No text input provided")
        return jsonify({"error": "Text input is required"}), 400

    # Get aspect ratio
    aspect_ratio = request.form.get('aspect_ratio', '1:1')

    logger.info(f"GENERATE_TEXT: Received text input ({len(user_text)} chars)")
    logger.info(f"GENERATE_TEXT: Aspect ratio: {aspect_ratio}")

    # Handle multiple file uploads (up to 5 style + 5 persona = 10 total)
    reference_images = {'style': [], 'persona': []}

    # Process style images (multiple)
    style_files = request.files.getlist('style_images')
    for i, file in enumerate(style_files[:5]):  # Max 5 style images
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"style_{uuid.uuid4()}_{i}.png")
            filepath = app.config['UPLOAD_FOLDER'] / filename
            file.save(filepath)
            reference_images['style'].append(str(filepath))
            logger.info(f"GENERATE_TEXT: STYLE image {i+1} uploaded: {filename}")

    # Process persona/character images (multiple)
    persona_files = request.files.getlist('persona_images')
    for i, file in enumerate(persona_files[:5]):  # Max 5 persona images
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"persona_{uuid.uuid4()}_{i}.png")
            filepath = app.config['UPLOAD_FOLDER'] / filename
            file.save(filepath)
            reference_images['persona'].append(str(filepath))
            logger.info(f"GENERATE_TEXT: PERSONA image {i+1} uploaded: {filename}")

    total_refs = len(reference_images['style']) + len(reference_images['persona'])
    logger.info(f"GENERATE_TEXT: Total reference images: {total_refs} (style: {len(reference_images['style'])}, persona: {len(reference_images['persona'])})")

    job_id = str(uuid.uuid4())
    text_preview = user_text[:100] + "..." if len(user_text) > 100 else user_text

    # Atomically create job if under concurrency limit
    if not job_db.create_job(job_id, input_mode='text', text_preview=text_preview):
        running_count = job_db.get_running_count()
        logger.warning(f"GENERATE_TEXT: At capacity ({running_count}/{job_db.MAX_CONCURRENT_JOBS})")
        # Cleanup uploaded files since we can't start the job
        for img_paths in reference_images.values():
            for img_path in img_paths:
                try:
                    if os.path.exists(img_path):
                        os.remove(img_path)
                except:
                    pass
        return jsonify({
            "error": f"Max concurrent jobs ({job_db.MAX_CONCURRENT_JOBS}) reached. {running_count} running.",
            "running_count": running_count,
            "max_concurrent": job_db.MAX_CONCURRENT_JOBS
        }), 429

    logger.info(f"GENERATE_TEXT: Created job {job_id}")

    # Run in background
    thread = threading.Thread(
        target=run_generator_async_text_mode,
        args=(job_id, user_text, reference_images, aspect_ratio)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "running",
        "input_mode": "text",
        "running_count": job_db.get_running_count(),
        "max_concurrent": job_db.MAX_CONCURRENT_JOBS
    })


def run_generator_async_text_mode(job_id, user_text, reference_images, aspect_ratio='1:1'):
    """Run generator in text input mode"""
    logger.info(f"BACKGROUND_TEXT: Starting text mode generation for job {job_id}")
    logger.info(f"BACKGROUND_TEXT: Text length: {len(user_text)} chars")
    logger.info(f"BACKGROUND_TEXT: Reference images - style: {len(reference_images.get('style', []))}, persona: {len(reference_images.get('persona', []))}")
    logger.info(f"BACKGROUND_TEXT: Aspect ratio: {aspect_ratio}")

    try:
        env = os.environ.copy()
        # Use current STYLE or empty (don't hardcode - allows style reference to work)
        env['STYLE'] = os.environ.get('STYLE', '')
        env['INPUT_MODE'] = 'text'
        env['USER_TEXT_INPUT'] = user_text
        env['IMAGE_ASPECT_RATIO'] = aspect_ratio

        # Pass reference image paths as JSON env vars (supports multiple images)
        if reference_images.get('style'):
            env['REFERENCE_STYLE_IMAGES'] = json.dumps(reference_images['style'])
            logger.info(f"BACKGROUND_TEXT: Set REFERENCE_STYLE_IMAGES env var ({len(reference_images['style'])} images)")
        if reference_images.get('persona'):
            env['REFERENCE_PERSONA_IMAGES'] = json.dumps(reference_images['persona'])
            logger.info(f"BACKGROUND_TEXT: Set REFERENCE_PERSONA_IMAGES env var ({len(reference_images['persona'])} images)")

        venv_python = BASE_DIR / ".venv" / "bin" / "python"
        if not venv_python.exists():
            logger.warning(f"BACKGROUND_TEXT: venv not found, using system python")
            venv_python = "python"
        else:
            venv_python = str(venv_python)
            logger.info(f"BACKGROUND_TEXT: Using venv python: {venv_python}")

        logger.info(f"BACKGROUND_TEXT: Running subprocess...")
        # Run generator with job_id for session isolation
        result = subprocess.run(
            [venv_python, '-m', 'content_generator.main', '--job-id', job_id],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            env=env
        )

        # Extract post_id from output
        post_id = None
        for line in result.stdout.split('\n'):
            if 'post_text_' in line or 'post_' in line:
                # Extract post_id
                match = re.search(r'post_[a-z0-9_]+', line)
                if match:
                    post_id = match.group(0)
                    break

        logger.info(f"BACKGROUND_TEXT: Subprocess completed with return code {result.returncode}")

        if result.returncode == 0:
            logger.info(f"BACKGROUND_TEXT: Job {job_id} completed successfully. Post: {post_id}")
            logger.info(f"BACKGROUND_TEXT: stdout preview: {result.stdout[-200:] if result.stdout else 'None'}")
            job_db.complete_job(job_id, post_id)
        else:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            logger.error(f"BACKGROUND_TEXT: Job {job_id} failed: {error_msg}")
            logger.error(f"BACKGROUND_TEXT: Full stderr: {result.stderr}")
            job_db.fail_job(job_id, error_msg)

    except Exception as e:
        logger.error(f"BACKGROUND_TEXT: Exception in job {job_id}: {e}", exc_info=True)
        job_db.fail_job(job_id, str(e))

    finally:
        # Cleanup uploaded files (handle lists of paths)
        logger.info(f"BACKGROUND_TEXT: Cleaning up uploaded files...")
        for img_type, img_paths in reference_images.items():
            for img_path in img_paths:
                try:
                    if os.path.exists(img_path):
                        os.remove(img_path)
                        logger.info(f"BACKGROUND_TEXT: Deleted {img_type} image: {img_path}")
                except Exception as e:
                    logger.warning(f"BACKGROUND_TEXT: Failed to delete {img_path}: {e}")


@app.route('/update-style', methods=['POST'])
def update_style():
    """Update STYLE environment variable"""
    try:
        data = request.json
        new_style = data.get('style', '').strip()
        
        # Allow empty style (useful when using style reference images)
        # if not new_style:
        #     return jsonify({"error": "Style cannot be empty"}), 400
        
        # Update environment variable (affects next generation only)
        os.environ['STYLE'] = new_style
        
        if new_style:
            message = f"Style updated to: '{new_style[:50]}...' Will apply to next generation."
        else:
            message = "Style cleared (empty). Perfect for using style reference images!"
        
        return jsonify({
            "status": "success",
            "style": new_style,
            "message": message
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/status/<job_id>')
def status(job_id):
    """Check generation job status"""
    job = job_db.get_job(job_id)

    if not job:
        logger.warning(f"STATUS: Job {job_id} not found")
        return jsonify({"error": "Job not found"}), 404

    logger.debug(f"STATUS: Job {job_id} status: {job.get('status')}")
    return jsonify(job)


@app.route('/post/<post_id>')
def post_detail(post_id):
    """Detailed view of a single post"""
    post_dir = OUTPUT_DIR / post_id
    md_file = post_dir / f"{post_id}_content.md"
    
    if not md_file.exists():
        return "Post not found", 404
    
    # Read markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Parse metadata
    metadata = {
        "post_id": post_id,
        "title": "Untitled",
        "caption": "",
        "hashtags": [],
        "image_texts": [],
        "category": "",
        "theme": "",
        "generated": ""
    }
    
    lines = md_content.split('\n')
    current_section = None
    
    for line in lines:
        if line.startswith('# '):
            metadata['title'] = line[2:].strip()
        elif '**Category:**' in line:
            metadata['category'] = line.split('**Category:**')[1].strip()
        elif '**Theme:**' in line:
            metadata['theme'] = line.split('**Theme:**')[1].strip()
        elif '**Generated:**' in line:
            metadata['generated'] = line.split('**Generated:**')[1].strip()
        elif line.startswith('## Caption'):
            current_section = 'caption'
        elif line.startswith('## Hashtags'):
            current_section = 'hashtags'
        elif line.startswith('## Image Texts'):
            current_section = 'image_texts'
        elif line.startswith('##'):
            current_section = None
        elif current_section == 'caption' and line.strip() and not line.startswith('---'):
            metadata['caption'] = line.strip()
        elif current_section == 'hashtags' and line.strip().startswith('#'):
            metadata['hashtags'].extend(line.strip().split())
        elif current_section == 'image_texts' and line.strip() and line[0].isdigit():
            # Extract text from "1. **Text**"
            if '**' in line:
                text = line.split('**')[1] if len(line.split('**')) > 1 else line
                metadata['image_texts'].append(text)
    
    # Get images
    images_dir = post_dir / "images"
    images = []
    if images_dir.exists():
        for img_file in sorted(images_dir.glob("slide_*.png")):
            images.append({
                "filename": img_file.name,
                "url": f"/static/posts/{post_id}/images/{img_file.name}",
                "index": len(images) + 1
            })
    
    metadata['images'] = images
    metadata['total_images'] = len(images)
    
    return render_template('post_detail.html', post=metadata)


@app.route('/download/<post_id>')
def download_post(post_id):
    """Download post as ZIP file with content.txt and all images"""
    logger.info(f"DOWNLOAD: Request for post {post_id}")
    
    post_dir = OUTPUT_DIR / post_id
    md_file = post_dir / f"{post_id}_content.md"
    
    if not md_file.exists():
        logger.error(f"DOWNLOAD: Post {post_id} not found at {md_file}")
        return "Post not found", 404
    
    # Read metadata
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Parse content
    title = ""
    caption = ""
    hashtags = []
    image_texts = []
    
    lines = md_content.split('\n')
    current_section = None
    
    for line in lines:
        if line.startswith('# '):
            title = line[2:].strip()
        elif line.startswith('## Caption'):
            current_section = 'caption'
        elif line.startswith('## Hashtags'):
            current_section = 'hashtags'
        elif line.startswith('## Image Texts'):
            current_section = 'image_texts'
        elif line.startswith('##'):
            current_section = None
        elif current_section == 'caption' and line.strip() and not line.startswith('---'):
            if not caption:  # Get first non-empty line
                caption = line.strip()
        elif current_section == 'hashtags' and line.strip().startswith('#'):
            hashtags.extend(line.strip().split())
        elif current_section == 'image_texts' and line.strip() and line[0].isdigit():
            if '**' in line:
                text = line.split('**')[1] if len(line.split('**')) > 1 else line
                image_texts.append(text)
    
    # Create ZIP in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add content.txt
        content_txt = f"""Title: {title}

Caption:
{caption}

Hashtags:
{' '.join(hashtags)}

Slide Texts:
"""
        for i, text in enumerate(image_texts, 1):
            content_txt += f"{i}. {text}\n"
        
        zf.writestr('post_content.txt', content_txt)
        
        # Add all images
        images_dir = post_dir / "images"
        if images_dir.exists():
            for img_file in sorted(images_dir.glob("slide_*.png")):
                zf.write(img_file, f"images/{img_file.name}")
    
    memory_file.seek(0)
    
    logger.info(f"DOWNLOAD: Created ZIP for {post_id} with {len(image_texts)} slides")
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{post_id}_carousel.zip'
    )


@app.route('/static/posts/<path:filepath>')
def serve_post_files(filepath):
    """Serve post images and files"""
    file_path = OUTPUT_DIR / filepath
    if file_path.exists() and file_path.is_file():
        return send_file(file_path)
    return "File not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

