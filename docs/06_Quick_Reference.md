# ADK Quick Reference Guide

## Basic Setup

```python
# Installation
pip install google-adk

# API Key setup
export GOOGLE_API_KEY="YOUR_KEY"
export GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Or for Vertex AI
export GOOGLE_CLOUD_PROJECT="PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
gcloud auth application-default login
```

## Simple Agent

```python
from google.adk.agents import Agent

agent = Agent(
    model='gemini-2.5-flash',
    name='my_agent',
    instruction='You are a helpful assistant'
)

# Run
# adk web
# or
# adk run my_agent
```

## Agent Types

### LLM Agent
```python
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="Assistant",
    model="gemini-2.5-flash",
    instruction="Your instructions here",
    tools=[tool1, tool2],
    output_key="result"  # Optional: saves output to state
)
```

### Sequential Agent
```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="Pipeline",
    sub_agents=[agent1, agent2, agent3]
)
```

### Parallel Agent
```python
from google.adk.agents import ParallelAgent

parallel = ParallelAgent(
    name="ParallelTasks",
    sub_agents=[agent1, agent2, agent3]
)
```

### Loop Agent
```python
from google.adk.agents import LoopAgent

loop = LoopAgent(
    name="IterativeProcess",
    sub_agents=[agent1, agent2],
    max_iterations=5
)
```

## Tools

### Built-in Tools
```python
from google.adk.tools import google_search, code_execution

agent = Agent(
    tools=[google_search, code_execution]
)
```

### Custom Function Tool
```python
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

def my_tool(tool_context: ToolContext, param: str) -> dict:
    """Tool description for LLM"""
    # Your logic
    return {"result": "value"}

agent = Agent(
    tools=[FunctionTool(my_tool)]
)
```

### MCP Tools
```python
from google.adk.tools.mcp_tools import MCPToolset

mcp_tools = MCPToolset(
    server_uri="mcp://server.com",
    auth_token="TOKEN"
)

agent = Agent(
    tools=mcp_tools.get_tools()
)
```

## State Management

### Read State
```python
def my_tool(tool_context: ToolContext) -> dict:
    value = tool_context.state.get('key', 'default')
    return {"value": value}
```

### Write State
```python
def my_tool(tool_context: ToolContext, data: str) -> dict:
    tool_context.state['key'] = data
    return {"status": "saved"}
```

### Use State in Instructions
```python
agent = LlmAgent(
    instruction="User preferences: {user_prefs}"
)
```

## Memory

### Setup Memory
```python
from google.adk.memory import VertexAiMemoryBankService

memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id="ENGINE_ID"
)
```

### Use Memory in Agent
```python
from google.adk.tools import PreloadMemoryTool

agent = Agent(
    tools=[PreloadMemoryTool()],
    instruction="Use past conversations to personalize"
)
```

### Add to Memory
```python
await memory_service.add_session_to_memory(session)
```

### Search Memory
```python
results = await memory_service.search_memory(
    app_name="app",
    user_id="user",
    query="What did we discuss?"
)
```

## Callbacks

### Before Agent
```python
def before_agent(callback_context, request):
    # Runs before agent processes request
    return None  # Continue normally

agent = Agent(
    before_agent_callback=before_agent
)
```

### After Agent
```python
def after_agent(callback_context, response):
    # Runs after agent completes
    return None  # Use original response

agent = Agent(
    after_agent_callback=after_agent
)
```

### Before Model
```python
from google.adk.models import LlmRequest, LlmResponse

def before_model(callback_context, llm_request: LlmRequest):
    # Modify request or skip LLM call
    if "BLOCK" in llm_request.contents[-1].parts[0].text:
        return LlmResponse(content=...)  # Skip LLM
    return None  # Continue to LLM

agent = Agent(
    before_model_callback=before_model
)
```

### Before Tool
```python
def before_tool(callback_context, tool_name: str, **kwargs):
    # Validate or skip tool execution
    if not authorized:
        return {"error": "unauthorized"}  # Skip tool
    return None  # Continue with tool

agent = Agent(
    before_tool_callback=before_tool
)
```

## Runner

### Basic Usage
```python
from google.adk.runners import Runner
from google.genai.types import Content, Part

runner = Runner(
    agent=my_agent,
    app_name="my_app"
)

user_message = Content(parts=[Part(text="Hello")])

async for event in runner.run_async(
    user_id="user_123",
    session_id="session_001",
    new_message=user_message
):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

### With Services
```python
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()

runner = Runner(
    agent=my_agent,
    app_name="my_app",
    session_service=session_service,
    memory_service=memory_service
)
```

## A2A Protocol

### Expose Agent
```python
from google.adk.a2a import A2AServer

server = A2AServer(agent=my_agent, port=8080)
await server.start()
```

### Consume Remote Agent
```python
from google.adk.agents import RemoteA2aAgent

remote_agent = RemoteA2aAgent(
    name="RemoteAgent",
    url="https://remote-agent.com"
)

# Use as tool
agent = Agent(
    tools=[AgentTool(remote_agent)]
)
```

## Models

### Gemini (Default)
```python
agent = Agent(model="gemini-2.5-flash")
```

### Claude via Vertex AI
```python
from google.adk.models.anthropic_llm import Claude
from google.adk.models.registry import LLMRegistry

LLMRegistry.register(Claude)

agent = Agent(model="claude-3-sonnet@20240229")
```

### LiteLLM (OpenAI, Anthropic, etc.)
```python
from google.adk.models.lite_llm import LiteLlm

agent = Agent(
    model=LiteLlm(model="openai/gpt-4o")
)
```

### Ollama (Local)
```python
agent = Agent(
    model=LiteLlm(model="ollama_chat/llama3.2")
)
```

## CLI Commands

```bash
# Create new agent
adk create my_agent

# Run with web UI
adk web

# Run with CLI
adk run my_agent

# Run specific agent from directory
adk web --agents-dir ./agents

# With memory service
adk web --memory_service_uri="agentengine://ENGINE_ID"

# Specify port
adk web --port 8000
```

## Deployment

### Cloud Run
```bash
gcloud run deploy my-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Agent Engine
```python
# Deploy via console or:
gcloud alpha agent-engines deploy my-agent \
  --region us-central1 \
  --agent-file agent.py
```

## Environment Variables

```bash
# Gemini API
export GOOGLE_API_KEY="key"
export GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Vertex AI
export GOOGLE_CLOUD_PROJECT="project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI=TRUE

# Third-party APIs
export OPENAI_API_KEY="key"
export ANTHROPIC_API_KEY="key"
export FIRECRAWL_API_KEY="key"

# Ollama
export OLLAMA_API_BASE="http://localhost:11434"
```

## Common Patterns

### Multi-Tool Agent
```python
agent = Agent(
    model="gemini-2.5-flash",
    tools=[
        google_search,
        code_execution,
        FunctionTool(custom_tool)
    ]
)
```

### Agent Team
```python
coordinator = Agent(
    tools=[
        AgentTool(specialist1),
        AgentTool(specialist2)
    ]
)
```

### Pipeline
```python
pipeline = SequentialAgent(
    sub_agents=[
        data_collector,
        data_processor,
        data_saver
    ]
)
```

### Parallel Processing
```python
parallel_tasks = ParallelAgent(
    sub_agents=[task1, task2, task3]
)
```

### Iterative Refinement
```python
refinement = LoopAgent(
    sub_agents=[generator, evaluator, improver],
    max_iterations=5
)
```

## Debugging

### Enable Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### LiteLLM Debug
```python
import litellm
litellm._turn_on_debug()
```

### Inspect Events
```python
async for event in runner.run_async(...):
    print(f"Author: {event.author}")
    print(f"Content: {event.content}")
    print(f"Actions: {event.actions}")
```

## Error Handling

### Try-Catch in Tools
```python
def my_tool(tool_context: ToolContext) -> dict:
    try:
        result = risky_operation()
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
```

### Callbacks for Guardrails
```python
def safety_check(callback_context, llm_request):
    if contains_forbidden_content(llm_request):
        return LlmResponse(content=error_message)
    return None

agent = Agent(
    before_model_callback=safety_check
)
```

## Testing

```python
import pytest
from google.genai.types import Content, Part

@pytest.mark.asyncio
async def test_agent():
    agent = Agent(model="gemini-2.5-flash")
    runner = Runner(agent=agent)
    
    message = Content(parts=[Part(text="Hello")])
    
    final_response = None
    async for event in runner.run_async(
        user_id="test",
        session_id="test",
        new_message=message
    ):
        if event.is_final_response():
            final_response = event
    
    assert final_response is not None
    assert len(final_response.content.parts) > 0
```

## Resources

- [Official Documentation](https://google.github.io/adk-docs/)
- [GitHub Repository](https://github.com/google/adk-python)
- [API Reference (Python)](https://google.github.io/adk-docs/api-reference/python/)
- [Community Resources](https://google.github.io/adk-docs/community)

