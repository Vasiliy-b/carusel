"""
Save post metadata and content to markdown files.
"""
import os
import json
import logging
from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext
from datetime import datetime

logger = logging.getLogger(__name__)

def save_post_metadata(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Saves post metadata (title, caption, hashtags, prompts) as a markdown file.
    Reads from session state: current_post, copy_content, image_prompts, creative_brief
    """
    try:
        current_post = tool_context.state.get('current_post')
        if not current_post:
            return {"status": "error", "error": "No current_post in state"}
        
        post_id = current_post.get('post_id', 'unknown_post')
        
        # Read content from state
        copy_content_raw = tool_context.state.get('copy_content', '')
        image_prompts_raw = tool_context.state.get('image_prompts', '')
        creative_brief_raw = tool_context.state.get('creative_brief', '')
        
        # Parse JSON strings
        copy_content = {}
        if isinstance(copy_content_raw, str):
            try:
                # Remove markdown code blocks if present
                clean_str = copy_content_raw.strip()
                if clean_str.startswith('```json'):
                    clean_str = clean_str[7:]
                if clean_str.startswith('```'):
                    clean_str = clean_str[3:]
                if clean_str.endswith('```'):
                    clean_str = clean_str[:-3]
                copy_content = json.loads(clean_str.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse copy_content: {e}")
                copy_content = {"raw": copy_content_raw}
        
        image_prompts = []
        if isinstance(image_prompts_raw, str):
            try:
                clean_str = image_prompts_raw.strip()
                if clean_str.startswith('```json'):
                    clean_str = clean_str[7:]
                if clean_str.startswith('```'):
                    clean_str = clean_str[3:]
                if clean_str.endswith('```'):
                    clean_str = clean_str[:-3]
                image_prompts = json.loads(clean_str.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse image_prompts: {e}")
        
        creative_brief = {}
        if isinstance(creative_brief_raw, str):
            try:
                clean_str = creative_brief_raw.strip()
                if clean_str.startswith('```json'):
                    clean_str = clean_str[7:]
                if clean_str.startswith('```'):
                    clean_str = clean_str[3:]
                if clean_str.endswith('```'):
                    clean_str = clean_str[:-3]
                creative_brief = json.loads(clean_str.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse creative_brief: {e}")
        
        # Create output directory
        output_dir = os.path.join("output", "posts", post_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Build markdown content
        md_content = f"""# {copy_content.get('post_title', 'Untitled Post')}

**Post ID:** {post_id}  
**Category:** {current_post.get('category', 'N/A')}  
**Theme:** {current_post.get('theme', 'N/A')}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Caption

{copy_content.get('post_caption', 'No caption')}

---

## Hashtags

{' '.join(copy_content.get('hashtags', []))}

---

## Image Texts (Carousel Slides)

"""
        # Add image texts
        image_texts = copy_content.get('image_texts', [])
        for i, text in enumerate(image_texts, 1):
            md_content += f"{i}. **{text}**\n"
        
        md_content += f"""
---

## Creative Direction

**Carousel Style:** {creative_brief.get('carousel_style', 'N/A')}  
**Art Style:** {creative_brief.get('art_style', 'N/A')}  
**Colors:** {', '.join(creative_brief.get('colors', []))}  
**Text Placement:** {creative_brief.get('text_placement', 'N/A')}

**Reasoning:** {creative_brief.get('reasoning', 'N/A')}

---

## Image Generation Prompts

"""
        # Add prompts
        for prompt_data in image_prompts:
            i = prompt_data.get('i', '?')
            t = prompt_data.get('t', '')
            p = prompt_data.get('p', '')
            md_content += f"### Slide {i}: {t}\n\n```\n{p}\n```\n\n"
        
        md_content += f"""---

## Original Post Data

**Virality:** {current_post.get('virality', 'N/A')}  
**Engagement:** {current_post.get('engagement', 'N/A')}  
**Views:** {current_post.get('views', 'N/A')}  
**Saves:** {current_post.get('saves', 'N/A')}

**Original Content:**
```
{current_post.get('content', 'N/A')}
```
"""
        
        # Save to file
        filepath = os.path.join(output_dir, f"{post_id}_content.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"✅ Saved post metadata to: {filepath}")
        return {
            "status": "success",
            "filepath": filepath,
            "post_id": post_id
        }
        
    except Exception as e:
        logger.error(f"Error saving post metadata: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

