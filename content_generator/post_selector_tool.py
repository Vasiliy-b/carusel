"""
Tool to select current post from filtered_posts array based on iteration
"""
import logging
from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def select_current_post(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Select the current post to process based on iteration counter.
    This implements the waterfall: one post at a time through the pipeline.
    
    Returns:
        Current post data dictionary
    """
    try:
        # Get all filtered posts
        filtered_posts = tool_context.state.get('filtered_posts', [])
        
        if not filtered_posts:
            logger.error("No filtered_posts found in state!")
            return {
                "status": "error",
                "error": "No posts available to process"
            }
        
        # Get or initialize post counter
        current_index = tool_context.state.get('current_post_index', 0)
        
        logger.info(f"Selecting post {current_index + 1}/{len(filtered_posts)}")
        
        # Check if we've processed all posts
        if current_index >= len(filtered_posts):
            logger.info("All posts have been processed")
            return {
                "status": "complete",
                "message": f"All {len(filtered_posts)} posts processed"
            }
        
        # Get current post
        current_post = filtered_posts[current_index]
        
        # Increment counter for next iteration
        tool_context.state['current_post_index'] = current_index + 1
        
        # Store current post in state for other agents to access
        tool_context.state['current_post'] = current_post
        
        logger.info(f"✓ Selected post: {current_post.get('post_id', 'unknown')}")
        logger.info(f"  Category: {current_post.get('category', 'N/A')}")
        logger.info(f"  Theme: {current_post.get('theme', 'N/A')}")
        
        return {
            "status": "ready",
            "post_id": current_post.get('post_id'),
            "category": current_post.get('category'),
            "theme": current_post.get('theme'),
            "total_posts": len(filtered_posts),
            "current_index": current_index + 1
        }
        
    except Exception as e:
        logger.error(f"Error selecting current post: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def clear_post_state(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Clear post-specific state after processing completes.
    Prepares for next post iteration.
    
    Returns:
        Confirmation dictionary
    """
    try:
        # Clear post-specific data
        # CRITICAL: Reset image counter for next post!
        keys_to_clear = [
            'current_post',
            'content_analysis',
            'creative_brief',
            'copy_content',
            'image_prompts'
        ]
        
        cleared = []
        for key in keys_to_clear:
            if key in tool_context.state:
                del tool_context.state[key]
                cleared.append(key)
        
        # Reset counters (can't delete temp: keys, just set to 0)
        tool_context.state['temp:images_generated_count'] = 0
        cleared.append('temp:images_generated_count (reset)')
        
        logger.info(f"✓ Cleared {len(cleared)} state keys for next post")
        
        return {
            "status": "cleared",
            "keys_cleared": cleared
        }
        
    except Exception as e:
        logger.error(f"Error clearing state: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

