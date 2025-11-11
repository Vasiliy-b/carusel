# Memory, Sessions, and State in ADK

## Overview

ADK provides three levels of context management:
1. **Session** - Single conversation thread with history
2. **State** - Temporary data within current conversation  
3. **Memory** - Long-term searchable knowledge across sessions

## Core Concepts

### Session
Represents a single, ongoing interaction between a user and your agent system.

**Contains:**
- Chronological sequence of `Events` (messages, actions)
- Temporary data (`State`) relevant only during this conversation
- References to `Artifacts` (files, binary data)

**Key Properties:**
- `session_id` - Unique identifier
- `user_id` - Associated user
- `app_name` - Application identifier
- `events` - List of all events in chronological order
- `state` - Current state dictionary

### State
Data stored within a specific `Session`, relevant only to the current conversation.

**Use Cases:**
- Shopping cart items during chat
- User preferences mentioned in this session
- Temporary calculations or results
- Workflow progress within a turn

**Scope:**
- Session-level: Persists across turns in same session
- Invocation-level (`temp:` prefix): Cleared after each turn

### Memory
Searchable, cross-session information store.

**Use Cases:**
- User preferences from past conversations
- Historical interaction patterns
- Knowledge accumulated over time
- External knowledge bases

## Session Management

### Creating Sessions

```python
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()

session = await session_service.create_session(
    app_name="my_app",
    user_id="user_123",
    session_id="session_001"  # Optional, auto-generated if not provided
)
```

### Using Sessions with Runner

```python
from google.adk.runners import Runner

runner = Runner(
    agent=my_agent,
    app_name="my_app",
    session_service=session_service
)

# Runner automatically manages session
async for event in runner.run_async(
    user_id="user_123",
    session_id="session_001",
    new_message=user_input
):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

### Session Services

#### In-Memory (Development)
```python
from google.adk.sessions import InMemorySessionService

# Data lost on restart - for local testing only
session_service = InMemorySessionService()
```

#### Vertex AI Agent Engine (Production)
```python
# Persistent, managed by Google Cloud
# Automatically configured when deploying to Agent Engine
```

## State Management

### Reading State

```python
def my_tool(tool_context: ToolContext) -> dict:
    # Read from state
    user_name = tool_context.state.get('user_name', 'Guest')
    counter = tool_context.state.get('counter', 0)
    
    return {"message": f"Hello {user_name}, count: {counter}"}
```

### Writing State

```python
def my_tool(tool_context: ToolContext, name: str) -> dict:
    # Write to state
    tool_context.state['user_name'] = name
    tool_context.state['last_updated'] = datetime.now().isoformat()
    
    return {"status": "saved"}
```

### State Namespaces

#### Session State (Persistent across turns)
```python
# Persists across multiple user queries in same session
tool_context.state['shopping_cart'] = ['item1', 'item2']
```

#### Temporary State (Invocation-scoped)
```python
# Cleared after current invocation completes
tool_context.state['temp:calculation'] = intermediate_result
```

### State in Agent Instructions

```python
agent = LlmAgent(
    name="PersonalizedAgent",
    instruction="""
    User's preferences: {user_preferences}
    Current context: {conversation_context}
    Cart items: {shopping_cart}
    
    Use this information to personalize responses.
    """
)
```

### State Flow Between Agents

```python
# Agent 1 stores data
data_collector = LlmAgent(
    name="DataCollector",
    output_key="collected_data"  # Saves to state['collected_data']
)

# Agent 2 reads data
data_processor = LlmAgent(
    name="DataProcessor",
    instruction="Process this data: {collected_data}",  # Reads from state
    output_key="processed_data"
)

# Sequential workflow
pipeline = SequentialAgent(
    sub_agents=[data_collector, data_processor]
)
```

## Memory Management

### Memory Services

#### In-Memory Memory Service (Development)

```python
from google.adk.memory import InMemoryMemoryService

memory_service = InMemoryMemoryService()

# Add session to memory
await memory_service.add_session_to_memory(completed_session)

# Search memory
results = await memory_service.search_memory(
    app_name="my_app",
    user_id="user_123",
    query="What did we discuss about project X?"
)
```

#### Vertex AI Memory Bank (Production)

```python
from google.adk.memory import VertexAiMemoryBankService

memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id="AGENT_ENGINE_ID"
)

runner = Runner(
    agent=my_agent,
    memory_service=memory_service
)
```

### Using Memory in Agents

#### Option 1: Preload Memory Tool

```python
from google.adk.tools import PreloadMemoryTool

agent = Agent(
    name="MemoryAgent",
    tools=[PreloadMemoryTool()],  # Always loads memory at start
    instruction="Use past conversations to personalize responses"
)
```

#### Option 2: Load Memory Tool

```python
from google.adk.tools import LoadMemoryTool

agent = Agent(
    name="MemoryAgent",
    tools=[LoadMemoryTool()],  # Loads memory when agent decides
    instruction="Use load_memory tool when you need past conversation context"
)
```

#### Option 3: Custom Memory Search

```python
from google.adk.tools.tool_context import ToolContext

async def search_past_conversations(
    tool_context: ToolContext,
    query: str
) -> dict:
    """Search past conversations"""
    results = await tool_context.search_memory(query)
    
    memories = []
    for result in results.memories:
        memories.append(result.content.parts[0].text)
    
    return {"memories": memories}
```

### Auto-Save to Memory

```python
from google import adk

async def auto_save_callback(callback_context):
    """Automatically save session to memory after agent completes"""
    await callback_context._invocation_context.memory_service.add_session_to_memory(
        callback_context._invocation_context.session
    )

agent = Agent(
    name="AutoSaveAgent",
    tools=[adk.tools.preload_memory_tool.PreloadMemoryTool()],
    after_agent_callback=auto_save_callback
)
```

### Multiple Memory Services

```python
class MultiMemoryAgent(Agent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Conversational memory
        self.conversation_memory = InMemoryMemoryService()
        
        # Document knowledge base  
        self.document_memory = VertexAiMemoryBankService(
            project="PROJECT_ID",
            location="LOCATION",
            agent_engine_id="DOC_ENGINE_ID"
        )
    
    async def run(self, request, **kwargs):
        query = request.parts[0].text
        
        # Search both memory sources
        conversation_context = await self.conversation_memory.search_memory(query)
        document_context = await self.document_memory.search_memory(query)
        
        # Combine contexts
        combined_prompt = f"""
        Past conversations: {conversation_context.memories}
        From documents: {document_context.memories}
        
        User query: {query}
        """
        
        return await self.llm.generate_content_async(combined_prompt)
```

## Events

Events are the basic unit of communication, representing things that happen during a session.

### Event Types

```python
from google.adk.events import Event
from google.genai.types import Content, Part

# User message event
user_event = Event(
    author="user",
    content=Content(role="user", parts=[Part(text="Hello")])
)

# Agent response event
agent_event = Event(
    author="agent_name",
    content=Content(role="model", parts=[Part(text="Hi there!")])
)

# Tool call event
tool_event = Event(
    author="agent_name",
    content=Content(
        role="model",
        parts=[Part(function_call=FunctionCall(name="my_tool", args={}))]
    )
)

# Tool response event
tool_response = Event(
    author="agent_name",
    content=Content(
        role="user",
        parts=[Part(function_response=FunctionResponse(name="my_tool", response={}))]
    )
)
```

### Event Actions

Events can carry actions for state/artifact changes:

```python
from google.adk.events import EventActions

event = Event(
    author="agent_name",
    content=Content(...),
    actions=EventActions(
        state_delta={"key": "value"},      # State changes
        artifact_delta={"file.txt": data}, # Artifact changes
        escalate=False,                     # Escalation signal
        require_confirmation=False          # Confirmation request
    )
)
```

### Accessing Event History

```python
# In a tool or callback
def my_tool(tool_context: ToolContext) -> dict:
    # Access session events
    session = tool_context.session
    
    # Get all events
    for event in session.events:
        print(f"{event.author}: {event.content}")
    
    # Get last N events
    recent_events = session.events[-5:]
    
    return {"status": "processed"}
```

## Artifacts

Handle files and binary data associated with sessions.

### Saving Artifacts

```python
from google.adk.tools.tool_context import ToolContext

def save_report(tool_context: ToolContext, data: str) -> dict:
    """Save a report as an artifact"""
    
    # Save artifact
    artifact_path = tool_context.save_artifact(
        filename="report.txt",
        content=data.encode('utf-8')
    )
    
    return {
        "status": "saved",
        "path": artifact_path
    }
```

### Loading Artifacts

```python
def load_report(tool_context: ToolContext, filename: str) -> dict:
    """Load an artifact"""
    
    # Load artifact
    content = tool_context.load_artifact(filename)
    
    return {
        "content": content.decode('utf-8')
    }
```

### Artifact Services

#### In-Memory (Development)
```python
from google.adk.artifacts import InMemoryArtifactService

artifact_service = InMemoryArtifactService()
```

#### Google Cloud Storage (Production)
```python
from google.adk.artifacts import GcsArtifactService

artifact_service = GcsArtifactService(
    bucket_name="my-artifacts-bucket"
)
```

## Best Practices

### State Management
1. **Use descriptive keys** - `user_preferences` not `up`
2. **Clean up temporary data** - Use `temp:` prefix for invocation-scoped data
3. **Validate state reads** - Use `.get()` with defaults
4. **Document state schema** - Clear comments on expected state structure

### Memory Management
1. **Save selectively** - Don't store every session
2. **Clean queries** - Well-formed search queries get better results
3. **Chunk appropriately** - Break large documents into searchable chunks
4. **Monitor costs** - Memory Bank operations have costs

### Session Management
1. **Use persistent sessions** in production
2. **Implement session cleanup** - Remove old/abandoned sessions
3. **Handle session failures** - Graceful degradation if session service unavailable
4. **Log session IDs** - For debugging and auditing

### Event Management
1. **Don't mutate events** - Events are immutable records
2. **Use event filtering** - Filter by author, type when searching history
3. **Monitor event count** - Large event histories can impact performance

## Example: Complete Context Management

```python
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory import VertexAiMemoryBankService
from google.adk.runners import Runner
from google.adk.tools import PreloadMemoryTool, FunctionTool

# Custom tool using state
def update_preferences(tool_context: ToolContext, **prefs) -> dict:
    current_prefs = tool_context.state.get('user_preferences', {})
    current_prefs.update(prefs)
    tool_context.state['user_preferences'] = current_prefs
    return {"status": "updated", "preferences": current_prefs}

# Agent with state and memory
personalized_agent = LlmAgent(
    name="PersonalizedAgent",
    model="gemini-2.5-flash",
    instruction="""
    User preferences: {user_preferences}
    
    Use past conversations (via PreloadMemoryTool) and current preferences
    to provide personalized responses.
    """,
    tools=[
        PreloadMemoryTool(),
        FunctionTool(update_preferences)
    ]
)

# Setup services
session_service = InMemorySessionService()
memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id="ENGINE_ID"
)

# Create runner
runner = Runner(
    agent=personalized_agent,
    app_name="personalized_app",
    session_service=session_service,
    memory_service=memory_service
)

# Use the agent
async def chat(user_id: str, message: str):
    session_id = f"{user_id}_session"
    
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(parts=[Part(text=message)])
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)
```

