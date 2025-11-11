"""
Custom tools for Content Generator
"""
import asyncio
import io
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from google.cloud import storage
from google.adk.tools.tool_context import ToolContext
from .config import Config

logger = logging.getLogger(__name__)


def fetch_google_sheet_data(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Fetch data from public Google Sheet and filter by VIRALITY and ENGAGEMENT criteria.
    
    Returns:
        Dictionary containing filtered posts with metadata
    """
    try:
        logger.info("Fetching data from Google Sheets...")
        
        # Construct CSV export URL for INSTAGRAM sheet
        # GID for INSTAGRAM sheet is 904285398 (from the provided URL)
        sheet_url = f"https://docs.google.com/spreadsheets/d/{Config.SHEETS_ID}/export?format=csv&gid=904285398"
        
        # Fetch the sheet data
        response = requests.get(sheet_url, timeout=30)
        response.raise_for_status()
        
        # Parse CSV
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        
        logger.info(f"Fetched {len(df)} total posts from sheet")
        
        # Filter by VIRALITY column
        if 'VIRALITY' in df.columns:
            df = df[df['VIRALITY'].isin(Config.VIRALITY_FILTER)]
            logger.info(f"After VIRALITY filter: {len(df)} posts")
        
        # Filter by ENGAGEMENT column
        if 'ENGAGEMENT' in df.columns:
            df = df[df['ENGAGEMENT'].isin(Config.ENGAGEMENT_FILTER)]
            logger.info(f"After ENGAGEMENT filter: {len(df)} posts")
        
        # Extract relevant columns
        # Based on the sheet structure, we need: rewrited_script, url, posted date, category, etc.
        relevant_columns = [
            'url', 'posted date', 'category', 'theme', 
            'VIRALITY', 'ENGAGEMENT', 'original_script', 'rewrited_script'
        ]
        
        # Keep only columns that exist
        available_columns = [col for col in relevant_columns if col in df.columns]
        filtered_df = df[available_columns].copy()
        
        # Convert to list of dictionaries
        posts = filtered_df.to_dict('records')
        
        # Add row index for reference
        for idx, post in enumerate(posts):
            post['row_index'] = idx
            post['post_id'] = f"post_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Found {len(posts)} qualifying posts")
        
        # Pick 1 random post from qualified posts (ignore BATCH_SIZE)
        import random
        if posts:
            total_qualified = len(posts)
            random_post = random.choice(posts)
            posts = [random_post]  # Single random post
            logger.info(f"Randomly selected 1 post from {total_qualified} qualified posts")
            logger.info(f"Selected post: {random_post.get('post_id', 'N/A')}")
        else:
            logger.warning("No posts to select from!")
        
        logger.info(f"Successfully filtered {len(posts)} posts for processing")
        
        # Store in state for other agents to access
        tool_context.state['filtered_posts'] = posts
        tool_context.state['total_posts_found'] = len(posts)
        
        return {
            "status": "success",
            "total_posts": len(posts),
            "posts": posts,
            "summary": f"Found {len(posts)} posts matching criteria: VIRALITY in {Config.VIRALITY_FILTER}, ENGAGEMENT in {Config.ENGAGEMENT_FILTER}"
        }
        
    except Exception as e:
        logger.error(f"Error fetching sheet data: {e}")
        return {
            "status": "error",
            "error": str(e),
            "posts": []
        }


async def upload_to_gcs(
    tool_context: ToolContext,
    post_id: str,
    images: List[bytes],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Upload generated images to Google Cloud Storage.
    
    Args:
        post_id: Unique identifier for the post
        images: List of image bytes to upload
        metadata: Optional metadata to attach to images
    
    Returns:
        Dictionary with upload status and public URLs
    """
    try:
        logger.info(f"Uploading {len(images)} images for post {post_id} to GCS...")
        
        # Initialize GCS client
        storage_client = storage.Client(project=Config.PROJECT_ID)
        bucket = storage_client.bucket(Config.GCS_BUCKET)
        
        # Create bucket if it doesn't exist
        if not bucket.exists():
            logger.info(f"Creating GCS bucket: {Config.GCS_BUCKET}")
            bucket = storage_client.create_bucket(Config.GCS_BUCKET, location=Config.LOCATION)
            
            # Make public if configured
            if Config.GCS_BUCKET_PUBLIC:
                bucket.make_public(recursive=True, future=True)
        
        uploaded_urls = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for idx, image_bytes in enumerate(images):
            # Construct blob path
            blob_name = f"posts/{post_id}/image_{idx + 1}_{timestamp}.{Config.IMAGE_FORMAT.lower()}"
            blob = bucket.blob(blob_name)
            
            # Set metadata
            if metadata:
                blob.metadata = metadata
            
            # Upload with retry
            retry_count = 0
            while retry_count < Config.RETRY_ATTEMPTS:
                try:
                    blob.upload_from_string(
                        image_bytes,
                        content_type=f'image/{Config.IMAGE_FORMAT.lower()}'
                    )
                    
                    # Make public if configured
                    if Config.GCS_BUCKET_PUBLIC:
                        blob.make_public()
                    
                    # Get public URL
                    public_url = blob.public_url if Config.GCS_BUCKET_PUBLIC else f"gs://{Config.GCS_BUCKET}/{blob_name}"
                    uploaded_urls.append(public_url)
                    
                    logger.info(f"Uploaded image {idx + 1}/{len(images)}: {blob_name}")
                    break
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= Config.RETRY_ATTEMPTS:
                        raise
                    logger.warning(f"Upload attempt {retry_count} failed, retrying... {e}")
                    await asyncio.sleep(Config.RETRY_DELAY)
        
        folder_url = f"https://console.cloud.google.com/storage/browser/{Config.GCS_BUCKET}/posts/{post_id}"
        
        # Store in state
        tool_context.state[f'gcs_urls_{post_id}'] = uploaded_urls
        
        return {
            "status": "success",
            "post_id": post_id,
            "uploaded_count": len(uploaded_urls),
            "urls": uploaded_urls,
            "folder_url": folder_url
        }
        
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        return {
            "status": "error",
            "error": str(e),
            "urls": []
        }


async def update_sheet_metadata(
    tool_context: ToolContext,
    post_id: str,
    row_index: int,
    generated_header: str,
    generated_text: str,
    gcs_folder_url: str,
    creative_style: str
) -> Dict[str, Any]:
    """
    Update Google Sheet with generation results.
    
    Args:
        post_id: Post identifier
        row_index: Row index in original sheet
        generated_header: Generated header text
        generated_text: Generated post text
        gcs_folder_url: URL to GCS folder with images
        creative_style: 'narrative' or 'independent'
    
    Returns:
        Dictionary with update status
    """
    try:
        logger.info(f"Updating sheet metadata for post {post_id}...")
        
        # If we have service account credentials, use gspread
        if Config.SHEETS_SERVICE_ACCOUNT_PATH and os.path.exists(Config.SHEETS_SERVICE_ACCOUNT_PATH):
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                Config.SHEETS_SERVICE_ACCOUNT_PATH,
                scope
            )
            client = gspread.authorize(creds)
            
            # Open spreadsheet
            spreadsheet = client.open_by_key(Config.SHEETS_ID)
            
            if Config.OUTPUT_MODE == 'new_tab':
                # Create or get output sheet
                try:
                    worksheet = spreadsheet.worksheet(Config.OUTPUT_SHEET_NAME)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(
                        title=Config.OUTPUT_SHEET_NAME,
                        rows=1000,
                        cols=20
                    )
                    # Add headers
                    worksheet.append_row([
                        'post_id', 'row_index', 'generated_header', 'generated_text',
                        'creative_style', 'gcs_folder_url', 'generation_date', 'status'
                    ])
                
                # Append new row
                worksheet.append_row([
                    post_id,
                    row_index,
                    generated_header,
                    generated_text,
                    creative_style,
                    gcs_folder_url,
                    datetime.now().isoformat(),
                    'completed'
                ])
                
            elif Config.OUTPUT_MODE == 'new_columns':
                # Update existing row with new columns
                source_sheet = spreadsheet.worksheet(Config.SOURCE_SHEET_NAME)
                # Find or create columns
                # This is more complex - would need to find header row and add columns
                pass
            
            logger.info(f"Successfully updated sheet for post {post_id}")
            
            return {
                "status": "success",
                "post_id": post_id,
                "updated_at": datetime.now().isoformat()
            }
        else:
            # Fallback: Store locally or log
            logger.warning("No Sheets write credentials - storing metadata locally")
            
            # Store in state for now
            tool_context.state[f'metadata_{post_id}'] = {
                'generated_header': generated_header,
                'generated_text': generated_text,
                'gcs_folder_url': gcs_folder_url,
                'creative_style': creative_style,
                'generation_date': datetime.now().isoformat()
            }
            
            return {
                "status": "stored_locally",
                "post_id": post_id,
                "note": "Sheets write credentials not configured"
            }
            
    except Exception as e:
        logger.error(f"Error updating sheet: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def overlay_text_on_image(
    tool_context: ToolContext,
    image_bytes: bytes,
    header_text: str,
    position: str = 'top',
    font_size: int = 60,
    text_color: str = 'white',
    background_color: Optional[str] = None
) -> bytes:
    """
    Overlay text on image using PIL/Pillow (fallback if gemini-2.5-flash-image fails with text).
    
    Args:
        image_bytes: Original image bytes
        header_text: Text to overlay
        position: 'top', 'center', or 'bottom'
        font_size: Font size in pixels
        text_color: Color name or RGB tuple
        background_color: Optional background color for text
    
    Returns:
        Modified image bytes
    """
    try:
        logger.info(f"Overlaying text on image: '{header_text}'")
        
        # Open image
        image = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(image)
        
        # Try to use a nice font, fallback to default
        try:
            # Try common font paths
            font_paths = [
                '/System/Library/Fonts/Helvetica.ttc',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
                'C:\\Windows\\Fonts\\arial.ttf'  # Windows
            ]
            
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, font_size)
                    break
            
            if font is None:
                font = ImageFont.load_default()
                logger.warning("Using default font - custom font not found")
                
        except Exception as e:
            logger.warning(f"Error loading font: {e}, using default")
            font = ImageFont.load_default()
        
        # Calculate text size and position
        bbox = draw.textbbox((0, 0), header_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        img_width, img_height = image.size
        
        # Calculate position
        if position == 'top':
            x = (img_width - text_width) // 2
            y = 50
        elif position == 'center':
            x = (img_width - text_width) // 2
            y = (img_height - text_height) // 2
        else:  # bottom
            x = (img_width - text_width) // 2
            y = img_height - text_height - 50
        
        # Draw background if specified
        if background_color:
            padding = 20
            draw.rectangle(
                [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
                fill=background_color
            )
        
        # Draw text with outline for better visibility
        outline_color = 'black' if text_color == 'white' else 'white'
        outline_width = 3
        
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                draw.text((x + adj_x, y + adj_y), header_text, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((x, y), header_text, font=font, fill=text_color)
        
        # Convert back to bytes
        output = io.BytesIO()
        image.save(output, format=Config.IMAGE_FORMAT, quality=Config.IMAGE_QUALITY)
        output.seek(0)
        
        logger.info("Successfully overlaid text on image")
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error overlaying text: {e}")
        # Return original image if overlay fails
        return image_bytes


async def generate_image_from_prompt(
    tool_context: ToolContext,
    prompt_text: str,
    image_text: str
) -> Dict[str, Any]:
    """
    Generate an image using gemini-2.5-flash-image model directly.
    
    Args:
        prompt_text: Full detailed prompt for image generation
        image_text: The 1-2 word text to overlay on image
    
    Returns:
        Dictionary with image data (base64 or bytes)
    """
    try:
        logger.info(f"Generating image with gemini-2.5-flash-image: '{image_text}'")
        
        # Import Gemini SDK for direct API call
        from google.genai import types
        from google import genai
        
        # Create client
        client = genai.Client(
            vertexai=Config.USE_VERTEX_AI,
            project=Config.PROJECT_ID if Config.USE_VERTEX_AI else None,
            location=Config.LOCATION if Config.USE_VERTEX_AI else None
        )
        
        # Create the full prompt with style suffix
        if Config.STYLE:
            full_prompt = f"{prompt_text}, {Config.STYLE}"
            logger.info(f"✓ Appended STYLE suffix: '{Config.STYLE}'")
        else:
            full_prompt = f"{prompt_text}"
        
        logger.info(f"Calling gemini-2.5-flash-image API...")
        
        # Generate image (synchronous call, but wrapped in async)
        response = client.models.generate_content(
            model=Config.IMAGE_MODEL,
            contents=full_prompt
        )
        
        # Extract image from response
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    # Got image data
                    image_bytes = part.inline_data.data
                    logger.info(f"✓ Image generated successfully ({len(image_bytes)} bytes)")
                    
                    # CRITICAL: Save image immediately, DON'T return bytes to agent!
                    # Image bytes would explode the context
                    from .local_saver import save_image_local
                    
                    # Get current post ID
                    current_post = tool_context.state.get('current_post', {})
                    post_id = current_post.get('post_id', 'unknown_post') if isinstance(current_post, dict) else 'unknown_post'
                    
                    # Get image number from counter
                    image_num = tool_context.state.get('temp:images_generated_count', 0)
                    
                    # Save locally
                    saved_path = save_image_local(
                        post_id=post_id,
                        image_number=image_num,
                        image_bytes=image_bytes,
                        image_text=image_text
                    )
                    
                    logger.info(f"✓ Saved image locally: {saved_path}")
                    
                    # Return ONLY metadata, NO bytes!
                    return {
                        "status": "success",
                        "image_saved": saved_path,
                        "image_text": image_text,
                        "size_bytes": len(image_bytes)
                    }
        
        return {
            "status": "error",
            "error": "No image data in response"
        }
        
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def exit_image_loop(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Signal that all 10 images have been generated and loop should exit.
    Sets escalate=True to terminate the LoopAgent.
    
    Returns:
        Confirmation dictionary
    """
    logger.info("🛑 All images generated - exiting loop")
    tool_context.actions.escalate = True
    
    return {
        "status": "complete",
        "message": "All 10 images generated, loop terminated"
    }


def get_next_prompt_for_generation(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the next prompt from image_prompts array that needs to be generated.
    Tracks which images have been generated and returns the next one.
    
    Returns:
        Dictionary with prompt details for the next image to generate
    """
    try:
        # Get image prompts array from state
        image_prompts_raw = tool_context.state.get('image_prompts', [])
        
        logger.info(f"DEBUG: image_prompts_raw type: {type(image_prompts_raw)}, value: {str(image_prompts_raw)[:200]if image_prompts_raw else 'None'}...")
        
        # Parse if it's a string (handle markdown-wrapped JSON)
        if isinstance(image_prompts_raw, str):
            from .utils import extract_json_from_text
            image_prompts = extract_json_from_text(image_prompts_raw)
            
            if image_prompts is None:
                logger.error(f"Could not parse JSON from image_prompts. Raw value: {image_prompts_raw[:200]}...")
                return {
                    "status": "error",
                    "error": "Failed to parse image_prompts JSON from state"
                }
        else:
            image_prompts = image_prompts_raw
        
        logger.info(f"DEBUG: Parsed {len(image_prompts) if image_prompts else 0} prompts from state")
        
        # Get or initialize generation counter
        images_generated = tool_context.state.get('temp:images_generated_count', 0)
        logger.info(f"DEBUG: images_generated count: {images_generated}")
        
        if images_generated >= len(image_prompts):
            return {
                "status": "complete",
                "message": "All images have been generated"
            }
        
        # Get the next prompt (using compact keys)
        current_prompt_data = image_prompts[images_generated]
        
        # Increment counter
        tool_context.state['temp:images_generated_count'] = images_generated + 1
        
        logger.info(f"Returning prompt {images_generated + 1}/{len(image_prompts)}")
        
        # Support both compact (i,t,p) and full (slide_number, image_text, prompt) formats
        return {
            "status": "ready",
            "image_text": current_prompt_data.get('t') or current_prompt_data.get('image_text', ''),
            "prompt": current_prompt_data.get('p') or current_prompt_data.get('prompt', '')
        }
        
    except Exception as e:
        logger.error(f"Error getting next prompt: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def batch_upload_images(
    tool_context: ToolContext,
    post_data: Dict[str, Any],
    image_data_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Batch upload all images for a post and update sheet.
    Combines upload_to_gcs and update_sheet_metadata for efficiency.
    
    Args:
        post_data: Original post data from sheet
        image_data_list: List of dicts with 'image_bytes', 'slide_number', 'prompt'
    
    Returns:
        Dictionary with complete upload and update status
    """
    try:
        post_id = post_data.get('post_id')
        row_index = post_data.get('row_index')
        
        logger.info(f"Batch uploading {len(image_data_list)} images for post {post_id}")
        
        # Extract image bytes
        image_bytes_list = [img_data['image_bytes'] for img_data in image_data_list]
        
        # Upload to GCS
        upload_result = asyncio.run(upload_to_gcs(
            tool_context,
            post_id,
            image_bytes_list,
            metadata={
                'post_id': post_id,
                'row_index': str(row_index),
                'generation_date': datetime.now().isoformat()
            }
        ))
        
        if upload_result['status'] != 'success':
            return upload_result
        
        # Get generated content from state
        # Parse copy_content JSON to extract data
        copy_content = tool_context.state.get('copy_content', {})
        if isinstance(copy_content, str):
            import json
            try:
                copy_content = json.loads(copy_content)
            except:
                pass
        
        generated_header = copy_content.get('post_title', 'N/A') if isinstance(copy_content, dict) else 'N/A'
        generated_text = copy_content.get('post_caption', 'N/A') if isinstance(copy_content, dict) else 'N/A'
        
        # Get creative style from brief
        creative_brief = tool_context.state.get('creative_brief', {})
        if isinstance(creative_brief, str):
            import json
            try:
                creative_brief = json.loads(creative_brief)
            except:
                pass
        
        creative_style = creative_brief.get('carousel_style', 'N/A') if isinstance(creative_brief, dict) else 'N/A'
        
        # Update sheet
        sheet_result = asyncio.run(update_sheet_metadata(
            tool_context,
            post_id,
            row_index,
            generated_header,
            generated_text,
            upload_result['folder_url'],
            creative_style
        ))
        
        return {
            "status": "success",
            "post_id": post_id,
            "images_uploaded": len(uploaded_urls),
            "urls": upload_result['urls'],
            "folder_url": upload_result['folder_url'],
            "sheet_updated": sheet_result['status'] == 'success'
        }
        
    except Exception as e:
        logger.error(f"Error in batch upload: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

