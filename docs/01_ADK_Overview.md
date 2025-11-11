# ADK (Agent Development Kit) - Complete Overview

## What is ADK?

Agent Development Kit (ADK) is a flexible and modular framework for **developing and deploying AI agents**. While optimized for Gemini and the Google ecosystem, ADK is:
- **Model-agnostic**
- **Deployment-agnostic**
- **Built for compatibility with other frameworks**

## Core Concepts

### 1. **Agent** - The Fundamental Worker Unit
Three main types:
- **LLM Agents** (`LlmAgent`, `Agent`) - Use Large Language Models for reasoning and dynamic decisions
- **Workflow Agents** (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) - Deterministic control flow
- **Custom Agents** - Extend `BaseAgent` for unique logic

### 2. **Tool** - Extend Agent Capabilities
Give agents abilities beyond conversation:
- Built-in tools (Search, Code Execution, BigQuery, etc.)
- MCP tools (Model Context Protocol)
- OpenAPI tools
- Custom function tools
- Third-party tools (Firecrawl, GitHub, Notion, etc.)

### 3. **Callbacks** - Hook into Agent Lifecycle
Custom code at specific execution points:
- `before_agent_callback` / `after_agent_callback`
- `before_model_callback` / `after_model_callback`
- `before_tool_callback` / `after_tool_callback`

### 4. **Session Management**
- **Session** - Single conversation thread with history (Events)
- **State** - Temporary data within current conversation
- **Memory** - Long-term, searchable knowledge across sessions

### 5. **Event Loop & Runtime**
- **Runner** - Orchestrates agent execution
- **Event** - Basic unit of communication
- Yield/pause/resume cycle for state management

## Key Capabilities

1. **Multi-Agent System Design** - Hierarchical agent composition
2. **Rich Tool Ecosystem** - Diverse capabilities via tools
3. **Flexible Orchestration** - Mix workflow and LLM-driven routing
4. **Integrated Developer Tooling** - CLI and Dev UI
5. **Native Streaming Support** - Text and audio bidirectional streaming
6. **Built-in Agent Evaluation** - Systematic performance assessment
7. **Broad LLM Support** - Gemini-optimized but model-agnostic
8. **Artifact Management** - Handle files and binary data
9. **Extensibility** - Open ecosystem for third-party tools
10. **State and Memory Management** - Automatic session handling

## Installation

```bash
# Python
pip install google-adk

# Go
go get google.golang.org/adk

# Java (Maven)
<dependency>
    <groupId>com.google.adk</groupId>
    <artifactId>google-adk</artifactId>
    <version>0.2.0</version>
</dependency>
```

## Quick Start

```python
from google.adk.agents import Agent

# Define a simple agent
root_agent = Agent(
    model='gemini-2.5-flash',
    name='my_agent',
    description='A helpful assistant',
    instruction='You are a helpful AI assistant.',
    tools=[my_custom_tool]
)

# Run locally
# adk web
# or
# adk run my_agent
```

## Architecture

ADK follows an event-driven architecture:
1. User sends query → Runner
2. Agent processes → Yields Events
3. Runner processes Events → Commits state changes
4. Cycle repeats until completion

## Next Steps

- Build multi-agent systems
- Integrate tools and MCP servers
- Configure callbacks for guardrails
- Deploy to production (Agent Engine, Cloud Run, GKE)

