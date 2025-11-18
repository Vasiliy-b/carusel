"""
Flask Web UI for Multi-Agent Content Generator
Simple interface for SMM team to trigger generations and browse results
"""
import os
import json
import subprocess
import uuid
import glob
import zipfile
import re
import logging
from datetime import datetime
from pathlib import Path
from io import BytesIO
from flask import Flask, render_template, jsonify, request, send_file
from werkzeug.utils import secure_filename
import threading

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

# Configure Flask for file uploads
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max
app.config['UPLOAD_FOLDER'] = Path(__file__).parent.parent / 'temp' / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Base paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "posts"
JOBS_FILE = BASE_DIR / "web_ui" / "jobs.json"

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure jobs file exists and clean up stale jobs on startup
if not JOBS_FILE.exists():
    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_FILE, 'w') as f:
        json.dump({}, f)
else:
    # Clean up any stale "running" jobs on server restart
    try:
        with open(JOBS_FILE, 'r') as f:
            jobs = json.load(f)
        
        # Mark all "running" jobs as "error" (server was restarted mid-generation)
        stale_count = 0
        for job_id, job in jobs.items():
            if job.get('status') == 'running':
                job['status'] = 'error'
                job['error'] = 'Server restarted during generation'
                job['completed_at'] = datetime.now().isoformat()
                stale_count += 1
        
        if stale_count > 0:
            with open(JOBS_FILE, 'w') as f:
                json.dump(jobs, f, indent=2)
            print(f"Cleaned up {stale_count} stale job(s)")
    except Exception as e:
        print(f"Error cleaning stale jobs: {e}")


def load_jobs():
    """Load jobs from persistent storage"""
    try:
        with open(JOBS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_jobs(jobs):
    """Save jobs to persistent storage"""
    try:
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs, f, indent=2)
    except Exception as e:
        print(f"Error saving jobs: {e}")


def get_active_job():
    """Get currently running job if any"""
    jobs = load_jobs()
    for job_id, job in jobs.items():
        if job.get('status') == 'running':
            return job_id, job
    return None, None


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
    """Run content generator in background"""
    logger.info(f"BACKGROUND: Starting sheet mode generation for job {job_id}")
    jobs = load_jobs()
    
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
        # Run generator with venv python
        result = subprocess.run(
            [venv_python, '-m', 'content_generator.main'],
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
            jobs[job_id] = {
                "status": "complete",
                "post_id": post_id,
                "completed_at": datetime.now().isoformat()
            }
        else:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            logger.error(f"BACKGROUND: Job {job_id} failed: {error_msg}")
            jobs[job_id] = {
                "status": "error",
                "error": error_msg,
                "completed_at": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"BACKGROUND: Exception in job {job_id}: {e}", exc_info=True)
        jobs[job_id] = {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }
    
    finally:
        save_jobs(jobs)
        logger.info(f"BACKGROUND: Job {job_id} status saved")


@app.route('/')
def index():
    """Homepage - Gallery view of all generated posts"""
    logger.info("INDEX: Loading homepage")
    posts = scan_generated_posts()
    logger.info(f"INDEX: Found {len(posts)} posts")
    
    # Check if there's an active job
    active_job_id, active_job = get_active_job()
    
    # Get current STYLE setting (empty by default)
    current_style = os.environ.get('STYLE', '')
    
    return render_template('index.html', 
                          posts=posts, 
                          active_job_id=active_job_id,
                          active_job=active_job,
                          current_style=current_style)


@app.route('/generate', methods=['POST'])
def generate():
    """Trigger new content generation"""
    logger.info("GENERATE: Sheet mode generation triggered")
    
    # Check if already running
    existing_job_id, existing_job = get_active_job()
    if existing_job_id:
        logger.warning(f"GENERATE: Already running job {existing_job_id}")
        return jsonify({
            "error": "Generation already in progress",
            "job_id": existing_job_id
        }), 409  # Conflict
    
    job_id = str(uuid.uuid4())
    logger.info(f"GENERATE: Created new job {job_id}")
    
    # Initialize job in persistent storage
    jobs = load_jobs()
    jobs[job_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat()
    }
    save_jobs(jobs)
    
    # Run in background thread
    thread = threading.Thread(target=run_generator_async, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "job_id": job_id,
        "status": "running"
    })


@app.route('/generate_from_text', methods=['POST'])
def generate_from_text():
    """Generate content from free-form text input with optional reference images"""
    logger.info("GENERATE_TEXT: Text mode generation triggered")
    
    # Check if already running
    existing_job_id, existing_job = get_active_job()
    if existing_job_id:
        logger.warning(f"GENERATE_TEXT: Already running job {existing_job_id}")
        return jsonify({
            "error": "Generation already in progress",
            "job_id": existing_job_id
        }), 409
    
    # Get text input
    user_text = request.form.get('text_input', '').strip()
    if not user_text:
        logger.error("GENERATE_TEXT: No text input provided")
        return jsonify({"error": "Text input is required"}), 400
    
    # Get aspect ratio
    aspect_ratio = request.form.get('aspect_ratio', '1:1')
    
    logger.info(f"GENERATE_TEXT: Received text input ({len(user_text)} chars)")
    logger.info(f"GENERATE_TEXT: Aspect ratio: {aspect_ratio}")
    
    # Handle file uploads
    reference_images = {}
    
    if 'style_image' in request.files:
        file = request.files['style_image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"style_{uuid.uuid4()}.png")
            filepath = app.config['UPLOAD_FOLDER'] / filename
            file.save(filepath)
            reference_images['style'] = str(filepath)
            logger.info(f"GENERATE_TEXT: STYLE image uploaded: {filename}")
    
    if 'persona_image' in request.files:
        file = request.files['persona_image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"persona_{uuid.uuid4()}.png")
            filepath = app.config['UPLOAD_FOLDER'] / filename
            file.save(filepath)
            reference_images['persona'] = str(filepath)
            logger.info(f"GENERATE_TEXT: PERSONA image uploaded: {filename}")
    
    job_id = str(uuid.uuid4())
    
    # Initialize job
    jobs = load_jobs()
    jobs[job_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "input_mode": "text",
        "text_input": user_text[:100] + "..." if len(user_text) > 100 else user_text
    }
    save_jobs(jobs)
    
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
        "input_mode": "text"
    })


def run_generator_async_text_mode(job_id, user_text, reference_images, aspect_ratio='1:1'):
    """Run generator in text input mode"""
    logger.info(f"BACKGROUND_TEXT: Starting text mode generation for job {job_id}")
    logger.info(f"BACKGROUND_TEXT: Text length: {len(user_text)} chars")
    logger.info(f"BACKGROUND_TEXT: Reference images: {list(reference_images.keys())}")
    logger.info(f"BACKGROUND_TEXT: Aspect ratio: {aspect_ratio}")
    
    jobs = load_jobs()
    
    try:
        env = os.environ.copy()
        # Use current STYLE or empty (don't hardcode - allows style reference to work)
        env['STYLE'] = os.environ.get('STYLE', '')
        env['INPUT_MODE'] = 'text'
        env['USER_TEXT_INPUT'] = user_text
        env['IMAGE_ASPECT_RATIO'] = aspect_ratio
        
        # Pass reference image paths as env vars
        if reference_images:
            if 'style' in reference_images:
                env['REFERENCE_STYLE_IMAGE'] = reference_images['style']
                logger.info(f"BACKGROUND_TEXT: Set REFERENCE_STYLE_IMAGE env var")
            if 'persona' in reference_images:
                env['REFERENCE_PERSONA_IMAGE'] = reference_images['persona']
                logger.info(f"BACKGROUND_TEXT: Set REFERENCE_PERSONA_IMAGE env var")
        
        venv_python = BASE_DIR / ".venv" / "bin" / "python"
        if not venv_python.exists():
            logger.warning(f"BACKGROUND_TEXT: venv not found, using system python")
            venv_python = "python"
        else:
            venv_python = str(venv_python)
            logger.info(f"BACKGROUND_TEXT: Using venv python: {venv_python}")
        
        logger.info(f"BACKGROUND_TEXT: Running subprocess...")
        result = subprocess.run(
            [venv_python, '-m', 'content_generator.main'],
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
            jobs[job_id] = {
                "status": "complete",
                "post_id": post_id,
                "input_mode": "text",
                "completed_at": datetime.now().isoformat()
            }
        else:
            error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
            logger.error(f"BACKGROUND_TEXT: Job {job_id} failed: {error_msg}")
            logger.error(f"BACKGROUND_TEXT: Full stderr: {result.stderr}")
            jobs[job_id] = {
                "status": "error",
                "error": error_msg,
                "completed_at": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"BACKGROUND_TEXT: Exception in job {job_id}: {e}", exc_info=True)
        jobs[job_id] = {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }
    
    finally:
        # Cleanup uploaded files
        logger.info(f"BACKGROUND_TEXT: Cleaning up uploaded files...")
        for img_type, img_path in reference_images.items():
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
                    logger.info(f"BACKGROUND_TEXT: Deleted {img_type} image: {img_path}")
            except Exception as e:
                logger.warning(f"BACKGROUND_TEXT: Failed to delete {img_path}: {e}")
        
        save_jobs(jobs)
        logger.info(f"BACKGROUND_TEXT: Job {job_id} finalized")


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
    jobs = load_jobs()
    
    if job_id not in jobs:
        logger.warning(f"STATUS: Job {job_id} not found")
        return jsonify({"error": "Job not found"}), 404
    
    job = jobs[job_id]
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

