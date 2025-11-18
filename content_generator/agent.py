"""
ADK agent module - exposes root_agent for ADK web/run commands
"""
import os

# Import factory function
from .orchestrator import create_root_agent_for_mode

# For ADK web/run compatibility, create agent at import time based on env
# Note: This will be recreated per subprocess, avoiding parent conflicts
input_mode = os.getenv('INPUT_MODE', 'sheet')
root_agent = create_root_agent_for_mode(input_mode)

# This is the agent that ADK will use when running:
#   adk web
#   adk run content_generator

__all__ = ['root_agent', 'create_root_agent_for_mode']

