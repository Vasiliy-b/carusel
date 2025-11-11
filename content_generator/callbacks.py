"""
Callbacks for monitoring, logging, and error handling
"""
import logging
from typing import Optional
from datetime import datetime

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from .config import Config

logger = logging.getLogger(__name__)


# ============================================
# MONITORING CALLBACKS
# ============================================

async def before_agent_monitor(callback_context: CallbackContext, request: types.Content):
    """
    Monitor and log before each agent execution
    """
    agent_name = callback_context.agent_name
    logger.info(f"🔷 Starting agent: {agent_name}")
    
    # Track start time in state
    callback_context.state[f'temp:agent_start_{agent_name}'] = datetime.now().isoformat()
    
    return None  # Continue with normal execution


async def after_agent_monitor(callback_context: CallbackContext, response: types.Content):
    """
    Monitor and log after each agent execution
    """
    agent_name = callback_context.agent_name
    
    # Calculate execution time
    start_time_key = f'temp:agent_start_{agent_name}'
    if start_time_key in callback_context.state:
        start_time = datetime.fromisoformat(callback_context.state[start_time_key])
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"🔶 Completed agent: {agent_name} (took {duration:.2f}s)")
        
        # Track in state for cost analysis
        if Config.TRACK_COSTS:
            execution_times = callback_context.state.get('agent_execution_times', {})
            execution_times[agent_name] = duration
            callback_context.state['agent_execution_times'] = execution_times
    else:
        logger.info(f"🔶 Completed agent: {agent_name}")
    
    return None  # Use original response


async def before_model_monitor(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Monitor LLM calls and implement safety guardrails
    """
    agent_name = callback_context.agent_name
    
    # Log model call
    logger.debug(f"📞 Model call from {agent_name}")
    
    # Track model calls for cost monitoring
    if Config.TRACK_COSTS:
        model_calls = callback_context.state.get('temp:model_call_count', 0)
        callback_context.state['temp:model_call_count'] = model_calls + 1
    
    # Optionally: Add safety checks here
    # Example: Check for inappropriate content, rate limits, etc.
    
    return None  # Proceed with model call


async def after_model_monitor(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Monitor LLM responses
    """
    agent_name = callback_context.agent_name
    logger.debug(f"📥 Model response received for {agent_name}")
    
    # Optionally: Post-process or validate response
    
    return None  # Use original response


async def before_tool_monitor(
    callback_context: CallbackContext,
    tool_name: str,
    **kwargs
):
    """
    Monitor tool executions
    """
    logger.info(f"🔧 Tool called: {tool_name}")
    logger.debug(f"  Arguments: {kwargs}")
    
    # Track tool usage
    tool_calls = callback_context.state.get('temp:tool_calls', [])
    tool_calls.append({
        'tool': tool_name,
        'agent': callback_context.agent_name,
        'timestamp': datetime.now().isoformat()
    })
    callback_context.state['temp:tool_calls'] = tool_calls
    
    return None  # Proceed with tool execution


async def after_tool_monitor(
    callback_context: CallbackContext,
    tool_name: str,
    result: dict,
    **kwargs
):
    """
    Monitor tool results
    """
    logger.info(f"🔨 Tool completed: {tool_name}")
    
    # Log result status if available
    if isinstance(result, dict) and 'status' in result:
        status = result['status']
        logger.debug(f"  Status: {status}")
        
        if status == 'error' and 'error' in result:
            logger.error(f"  Error: {result['error']}")
    
    return None  # Use original result


# ============================================
# ERROR HANDLING CALLBACKS
# ============================================

async def error_recovery_callback(
    callback_context: CallbackContext,
    error: Exception
):
    """
    Handle errors and attempt recovery
    """
    agent_name = callback_context.agent_name
    logger.error(f"❌ Error in {agent_name}: {str(error)}")
    
    # Log error details to state
    errors = callback_context.state.get('errors', [])
    errors.append({
        'agent': agent_name,
        'error': str(error),
        'timestamp': datetime.now().isoformat()
    })
    callback_context.state['errors'] = errors
    
    # Optionally: Implement retry logic or fallback strategies
    # For now, let error propagate
    raise error


# ============================================
# APPLY CALLBACKS TO AGENTS
# ============================================

def add_monitoring_to_agent(agent):
    """
    Add monitoring callbacks to an agent
    """
    agent.before_agent_callback = before_agent_monitor
    agent.after_agent_callback = after_agent_monitor
    agent.before_model_callback = before_model_monitor
    agent.after_model_callback = after_model_monitor
    agent.before_tool_callback = before_tool_monitor
    agent.after_tool_callback = after_tool_monitor
    
    return agent


def add_monitoring_to_all_agents(*agents):
    """
    Add monitoring callbacks to multiple agents
    """
    return [add_monitoring_to_agent(agent) for agent in agents]

