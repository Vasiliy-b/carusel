"""
Local file saver for posts and images
"""
import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def save_post_metadata_local(
    post_id: str,
    post_data: Dict[str, Any],
    generated_content: Dict[str, Any],
    output_dir: str = "output/posts"
) -> str:
    """
    Save post metadata to local .md file
    
    Args:
        post_id: Unique post identifier
        post_data: Original post data from sheet
        generated_content: Generated headers, captions, etc.
        output_dir: Directory to save files
    
    Returns:
        Path to saved file
    """
    try:
        # Create output directory
        post_dir = Path(output_dir) / post_id
        post_dir.mkdir(parents=True, exist_ok=True)
        
        # Create markdown file
        md_path = post_dir / f"{post_id}_metadata.md"
        
        # Build markdown content
        md_content = f"""# Post: {post_id}

## Generated Content

### Post Title
{generated_content.get('post_title', 'N/A')}

### Image Texts (per slide)
{json.dumps(generated_content.get('image_texts', []), indent=2)}

### Post Caption
{generated_content.get('post_caption', 'N/A')}

### Hashtags
{', '.join(generated_content.get('hashtags', []))}

## Original Post Data

### Category
{post_data.get('category', 'N/A')}

### Theme
{post_data.get('theme', 'N/A')}

### Virality
{post_data.get('VIRALITY', 'N/A')}

### Engagement
{post_data.get('ENGAGEMENT', 'N/A')}

### Original URL
{post_data.get('url', 'N/A')}

### Rewritten Script
```
{post_data.get('rewrited_script', 'N/A')}
```

## Generation Details

- **Generated At**: {datetime.now().isoformat()}
- **Post ID**: {post_id}
- **Row Index**: {post_data.get('row_index', 'N/A')}

"""
        
        # Write to file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"✓ Saved post metadata to {md_path}")
        return str(md_path)
        
    except Exception as e:
        logger.error(f"Error saving post metadata: {e}")
        return ""


def save_image_local(
    post_id: str,
    image_number: int,
    image_bytes: bytes,
    image_text: str,
    output_dir: str = "output/posts"
) -> str:
    """
    Save generated image to local file
    
    Args:
        post_id: Unique post identifier
        image_number: Image number (1-10)
        image_bytes: Image data
        image_text: The text overlay on the image
        output_dir: Directory to save files
    
    Returns:
        Path to saved file
    """
    try:
        # Create output directory
        post_dir = Path(output_dir) / post_id / "images"
        post_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize image_text for filename
        safe_text = image_text.replace(' ', '_').replace('/', '_')
        
        # Create filename
        image_path = post_dir / f"slide_{image_number:02d}_{safe_text}.png"
        
        # Write image
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        logger.info(f"✓ Saved image {image_number}/10 to {image_path}")
        return str(image_path)
        
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return ""


def save_image_prompts_local(
    post_id: str,
    prompts: List[Dict[str, Any]],
    output_dir: str = "output/posts"
) -> str:
    """
    Save image prompts to JSON file for reference
    
    Args:
        post_id: Unique post identifier
        prompts: List of prompt dictionaries
        output_dir: Directory to save files
    
    Returns:
        Path to saved file
    """
    try:
        post_dir = Path(output_dir) / post_id
        post_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = post_dir / f"{post_id}_prompts.json"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Saved prompts to {json_path}")
        return str(json_path)
        
    except Exception as e:
        logger.error(f"Error saving prompts: {e}")
        return ""


def create_post_summary(
    post_id: str,
    output_dir: str = "output/posts"
) -> str:
    """
    Create a summary index of all posts generated
    
    Args:
        post_id: Post to add to summary
        output_dir: Directory where posts are saved
    
    Returns:
        Path to summary file
    """
    try:
        summary_path = Path(output_dir) / "SUMMARY.md"
        
        # Read existing or create new
        if summary_path.exists():
            with open(summary_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# Generated Content Summary\n\n"
        
        # Add entry
        entry = f"\n## {post_id}\n- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- Location: `{post_id}/`\n\n"
        content += entry
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(summary_path)
        
    except Exception as e:
        logger.error(f"Error updating summary: {e}")
        return ""

