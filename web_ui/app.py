"""
Flask Web UI for Multi-Agent Content Generator
Simple interface for SMM team to trigger generations and browse results
"""
import os
import json
import subprocess
import uuid
import glob
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file
import threading

app = Flask(__name__)

# Base paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "posts"
JOBS_FILE = BASE_DIR / "web_ui" / "jobs.json"

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
    
    for post_dir in sorted(OUTPUT_DIR.iterdir(), reverse=True):
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
    jobs = load_jobs()
    
    try:
        # Set STYLE environment variable
        env = os.environ.copy()
        env['STYLE'] = "pastel colors, soft lighting, elegant, clean style, 3d render, high detail, 3d plasticine"
        
        # Use venv Python interpreter
        venv_python = BASE_DIR / ".venv" / "bin" / "python"
        if not venv_python.exists():
            # Fallback to system python if venv not found
            venv_python = "python"
        else:
            venv_python = str(venv_python)
        
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
        
        if result.returncode == 0:
            jobs[job_id] = {
                "status": "complete",
                "post_id": post_id,
                "completed_at": datetime.now().isoformat()
            }
        else:
            jobs[job_id] = {
                "status": "error",
                "error": result.stderr[-500:] if result.stderr else "Unknown error",  # Last 500 chars
                "completed_at": datetime.now().isoformat()
            }
            
    except Exception as e:
        jobs[job_id] = {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }
    
    finally:
        save_jobs(jobs)


@app.route('/')
def index():
    """Homepage - Gallery view of all generated posts"""
    posts = scan_generated_posts()
    
    # Check if there's an active job
    active_job_id, active_job = get_active_job()
    
    # Get current STYLE setting
    current_style = os.environ.get('STYLE', 'pastel colors, soft lighting, elegant, clean style, 3d render, high detail, 3d plasticine')
    
    return render_template('index.html', 
                          posts=posts, 
                          active_job_id=active_job_id,
                          active_job=active_job,
                          current_style=current_style)


@app.route('/generate', methods=['POST'])
def generate():
    """Trigger new content generation"""
    # Check if already running
    existing_job_id, existing_job = get_active_job()
    if existing_job_id:
        return jsonify({
            "error": "Generation already in progress",
            "job_id": existing_job_id
        }), 409  # Conflict
    
    job_id = str(uuid.uuid4())
    
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


@app.route('/update-style', methods=['POST'])
def update_style():
    """Update STYLE environment variable"""
    try:
        data = request.json
        new_style = data.get('style', '').strip()
        
        if not new_style:
            return jsonify({"error": "Style cannot be empty"}), 400
        
        # Update environment variable (affects next generation only)
        os.environ['STYLE'] = new_style
        
        return jsonify({
            "status": "success",
            "style": new_style,
            "message": "Style updated! Will apply to next generation."
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/status/<job_id>')
def status(job_id):
    """Check generation job status"""
    jobs = load_jobs()
    
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    
    job = jobs[job_id]
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


@app.route('/static/posts/<path:filepath>')
def serve_post_files(filepath):
    """Serve post images and files"""
    file_path = OUTPUT_DIR / filepath
    if file_path.exists() and file_path.is_file():
        return send_file(file_path)
    return "File not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

