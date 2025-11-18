"""
Context management and monitoring callbacks for preventing context blowout
"""
import logging
from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from google.adk.models import LlmRequest, LlmResponse

logger = logging.getLogger(__name__)

# Track context usage across agents
context_stats = {
    "max_tokens_seen": 0,
    "agent_token_counts": {},
    "warnings_issued": 0
}


def estimate_token_count(content: types.Content) -> int:
    """
    Rough estimation of token count from content.
    ~4 characters per token is a common approximation.
    """
    if not content or not content.parts:
        return 0
    
    total_chars = 0
    for part in content.parts:
        if hasattr(part, 'text') and part.text:
            total_chars += len(part.text)
        elif hasattr(part, 'inline_data') and part.inline_data:
            # Images/binary data - rough estimate
            total_chars += 1000  # Placeholder
    
    return total_chars // 4  # Rough token estimation


async def before_agent_monitor(
    callback_context: CallbackContext,
    request: types.Content
) -> Optional[types.Content]:
    """
    Monitor context before agent execution.
    Log warnings if context is growing too large.
    """
    try:
        agent_name = callback_context.agent_name or "Unknown"
        
        # Estimate token count
        token_count = estimate_token_count(request)
        
        # Track per-agent stats
        if agent_name not in context_stats["agent_token_counts"]:
            context_stats["agent_token_counts"][agent_name] = []
        
        context_stats["agent_token_counts"][agent_name].append(token_count)
        
        # Update max seen
        if token_count > context_stats["max_tokens_seen"]:
            context_stats["max_tokens_seen"] = token_count
        
        # Issue warnings at thresholds
        if token_count > 50000:
            context_stats["warnings_issued"] += 1
            logger.warning(
                f"⚠️  HIGH CONTEXT WARNING: {agent_name} has ~{token_count:,} tokens "
                f"(Max seen: {context_stats['max_tokens_seen']:,})"
            )
            
            # Log state size if available
            if hasattr(callback_context, 'invocation_context') and callback_context.invocation_context:
                state = callback_context.invocation_context.session.state
                state_size = len(str(state))
                logger.warning(f"   State size: {state_size:,} characters")
        
        elif token_count > 30000:
            logger.info(
                f"ℹ️  Context usage: {agent_name} ~{token_count:,} tokens"
            )
        
        # Log context stats every 5 agents
        if len(context_stats["agent_token_counts"]) % 5 == 0:
            avg_tokens = sum(
                sum(counts) / len(counts) 
                for counts in context_stats["agent_token_counts"].values()
                if counts
            ) / len(context_stats["agent_token_counts"])
            
            logger.info(
                f"📊 Context Stats: Avg={avg_tokens:.0f} tokens, "
                f"Max={context_stats['max_tokens_seen']:,}, "
                f"Warnings={context_stats['warnings_issued']}"
            )
        
    except Exception as e:
        logger.error(f"Error in before_agent_monitor: {e}")
    
    # Don't modify the request
    return None


async def after_agent_monitor(
    callback_context: CallbackContext,
    response: types.Content
) -> Optional[types.Content]:
    """
    Monitor context after agent execution.
    Trigger aggressive cleanup if needed.
    """
    try:
        agent_name = callback_context.agent_name or "Unknown"
        
        # Check if this is end of a post processing cycle
        if agent_name == "StateCleaner":
            logger.info("🧹 Post processing complete, state cleaned")
            
            # Reset per-post tracking
            if hasattr(callback_context, 'invocation_context') and callback_context.invocation_context:
                state = callback_context.invocation_context.session.state
                
                # Count remaining state keys
                temp_keys = [k for k in state.keys() if k.startswith('temp:')]
                persistent_keys = [k for k in state.keys() if not k.startswith('temp:')]
                
                logger.debug(
                    f"   State after cleanup: {len(persistent_keys)} persistent keys, "
                    f"{len(temp_keys)} temp keys"
                )
        
        # Monitor image generation completion
        if "ImageGenerator" in agent_name:
            logger.debug(f"✓ {agent_name} completed")
        
    except Exception as e:
        logger.error(f"Error in after_agent_monitor: {e}")
    
    # Don't modify the response
    return None


async def before_model_monitor(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Monitor before LLM API calls.
    Could implement rate limiting or cost tracking here.
    """
    try:
        agent_name = callback_context.agent_name or "Unknown"
        model = getattr(llm_request, 'model', 'unknown')
        
        # Log expensive image generation calls
        if 'image' in model.lower():
            logger.debug(f"🎨 Image generation API call: {agent_name}")
        
    except Exception as e:
        logger.error(f"Error in before_model_monitor: {e}")
    
    # Proceed with model call
    return None


async def after_model_monitor(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Monitor after LLM API calls.
    Track API usage and costs.
    """
    try:
        # Could track token usage from response metadata here
        pass
        
    except Exception as e:
        logger.error(f"Error in after_model_monitor: {e}")
    
    # Use original response
    return None


def get_context_stats() -> dict:
    """
    Get current context statistics.
    Useful for debugging and monitoring.
    """
    return {
        "max_tokens_seen": context_stats["max_tokens_seen"],
        "total_agents": len(context_stats["agent_token_counts"]),
        "warnings_issued": context_stats["warnings_issued"],
        "agent_breakdown": {
            agent: {
                "calls": len(counts),
                "avg_tokens": sum(counts) / len(counts) if counts else 0,
                "max_tokens": max(counts) if counts else 0
            }
            for agent, counts in context_stats["agent_token_counts"].items()
        }
    }


def reset_context_stats():
    """Reset context statistics (e.g., between runs)"""
    context_stats["max_tokens_seen"] = 0
    context_stats["agent_token_counts"].clear()
    context_stats["warnings_issued"] = 0
    logger.info("📊 Context statistics reset")

