"""
ADK agent module - exposes root_agent for ADK web/run commands
"""
from .orchestrator import root_agent

# This is the agent that ADK will use when running:
#   adk web
#   adk run content_generator
# The agent must be named 'root_agent' for ADK compatibility

__all__ = ['root_agent']

