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
            logger.info("All posts have been processed - escalating to exit loop")
            # Signal to LoopAgent to terminate
            tool_context.actions.escalate = True
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
        
        # CRITICAL: Also store the actual content text separately for ContentAnalyzer
        # Try rewrited_script first, fallback to original_script
        content_text = current_post.get('rewrited_script') or current_post.get('original_script', '')
        tool_context.state['post_content_text'] = content_text
        
        # Check if style reference is present and create flag for agents
        has_style_ref = 'generation_reference_images' in tool_context.state and 'style' in tool_context.state.get('generation_reference_images', {})
        has_persona_ref = 'generation_reference_images' in tool_context.state and 'persona' in tool_context.state.get('generation_reference_images', {})
        
        tool_context.state['has_style_reference'] = has_style_ref
        tool_context.state['has_persona_reference'] = has_persona_ref

        # Check if text input mode (for flexible text length on images)
        is_text_mode = tool_context.state.get('input_mode') == 'text'
        tool_context.state['is_text_mode'] = is_text_mode

        logger.info(f"✓ Selected post: {current_post.get('post_id', 'unknown')}")
        logger.info(f"  Category: {current_post.get('category', 'N/A')}")
        logger.info(f"  Theme: {current_post.get('theme', 'N/A')}")
        logger.info(f"  Content length: {len(content_text)} chars")
        logger.info(f"  Content preview: {content_text[:100]}...")
        logger.info(f"  Style reference: {has_style_ref}")
        logger.info(f"  Persona reference: {has_persona_ref}")
        logger.info(f"  Text mode (flexible text): {is_text_mode}")
        
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
    Also signals loop termination since we only process 1 post.
    
    Returns:
        Confirmation dictionary
    """
    try:
        logger.info("CLEAR_STATE: Clearing post-specific state and terminating loop")
        
        # Clear post-specific data
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
                try:
                    # State doesn't support .pop(), use del
                    del tool_context.state[key]
                    cleared.append(key)
                except Exception as e:
                    logger.warning(f"CLEAR_STATE: Could not clear {key}: {e}")
        
        # Reset counters
        tool_context.state['temp:images_generated_count'] = 0
        cleared.append('temp:images_generated_count (reset)')
        
        # CRITICAL: Signal loop to exit since we're done with this post
        # In single-post mode, after one post is done, we should exit
        tool_context.actions.escalate = True
        
        logger.info(f"CLEAR_STATE: ✓ Cleared {len(cleared)} keys and signaled loop exit")
        
        return {
            "status": "cleared",
            "keys_cleared": cleared,
            "loop_terminated": True
        }
        
    except Exception as e:
        logger.error(f"CLEAR_STATE: Error: {e}", exc_info=True)
        # Still try to escalate even if clearing failed
        tool_context.actions.escalate = True
        return {
            "status": "error",
            "error": str(e)
        }

