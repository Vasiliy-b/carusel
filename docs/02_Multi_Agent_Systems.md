# Multi-Agent Systems in ADK

## Overview

Multi-agent systems allow you to compose multiple specialized agents in a hierarchy to create sophisticated, modular applications. Complex coordination and delegation become possible through:

1. **LLM-driven transfer** - Dynamic routing based on LLM decisions
2. **Explicit AgentTool invocation** - Programmatic agent delegation
3. **Workflow orchestration** - Deterministic patterns (Sequential, Parallel, Loop)

## Agent Types

### 1. LLM Agents (`LlmAgent`)
**Core Engine:** Large Language Model
**Use For:** 
- Reasoning and generation
- Dynamic decision making
- Tool use based on context
- Language-centric tasks

```python
from google.adk.agents import LlmAgent

research_agent = LlmAgent(
    name="ResearchAgent",
    model="gemini-2.5-flash",
    instruction="You research topics thoroughly using available tools",
    tools=[google_search, web_scraper],
    output_key="research_results"
)
```

### 2. Sequential Agents
**Execution:** Sub-agents run one after another in order
**Use For:** 
- Fixed, strict execution order
- Pipeline workflows
- Dependencies between steps

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="CodePipeline",
    sub_agents=[
        code_writer_agent,
        code_reviewer_agent,
        code_refactorer_agent
    ],
    description="Writes, reviews, and refactors code in sequence"
)
```

**Key Feature:** Output from each agent flows to next via `output_key` stored in state.

### 3. Parallel Agents
**Execution:** Sub-agents run concurrently
**Use For:**
- Independent tasks
- Speed optimization
- Multi-source data retrieval
- No shared state requirements

```python
from google.adk.agents import ParallelAgent

parallel_research = ParallelAgent(
    name="ParallelResearcher",
    sub_agents=[
        renewable_energy_agent,
        ev_technology_agent,
        carbon_capture_agent
    ],
    description="Researches multiple topics simultaneously"
)
```

**Important:** Sub-agents run independently. No automatic state sharing. Use external state management or post-processing if needed.

### 4. Loop Agents
**Execution:** Repeatedly runs sub-agents until termination
**Use For:**
- Iterative refinement
- Repeated validation
- Feedback loops

```python
from google.adk.agents import LoopAgent

refinement_loop = LoopAgent(
    name="DocumentRefiner",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=5,
    description="Iteratively improves document quality"
)
```

**Termination Strategies:**
- Max iterations limit
- Sub-agent escalation (tool calling `exit_loop`)
- Custom condition evaluation

### 5. Custom Agents
**Extension:** Direct `BaseAgent` subclass
**Use For:**
- Unique orchestration logic
- Specific control flows
- Specialized integrations

## Building Multi-Agent Systems

### Pattern 1: Hierarchical Delegation

```python
# Coordinator delegates to specialists
coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.5-flash",
    instruction="Route tasks to specialized agents",
    tools=[
        AgentTool(finance_agent),
        AgentTool(legal_agent),
        AgentTool(technical_agent)
    ]
)
```

### Pattern 2: Pipeline Processing

```python
# Sequential workflow
data_pipeline = SequentialAgent(
    name="DataPipeline",
    sub_agents=[
        data_ingestion_agent,
        data_validation_agent,
        data_transformation_agent,
        data_storage_agent
    ]
)
```

### Pattern 3: Parallel-Then-Merge

```python
# Parallel research, then synthesis
parallel_phase = ParallelAgent(
    name="ParallelResearch",
    sub_agents=[researcher1, researcher2, researcher3]
)

synthesis_agent = LlmAgent(
    name="Synthesizer",
    instruction="Combine research from: {researcher1_result}, {researcher2_result}, {researcher3_result}"
)

research_pipeline = SequentialAgent(
    name="ResearchPipeline",
    sub_agents=[parallel_phase, synthesis_agent]
)
```

### Pattern 4: Iterative Improvement

```python
# Loop until quality threshold met
improvement_loop = LoopAgent(
    name="QualityLoop",
    sub_agents=[
        generator_agent,
        evaluator_agent,
        improver_agent
    ],
    max_iterations=10
)
```

## State Management Across Agents

### Using output_key for Data Flow

```python
agent1 = LlmAgent(
    name="DataCollector",
    output_key="raw_data"  # Stores output in state['raw_data']
)

agent2 = LlmAgent(
    name="DataProcessor",
    instruction="Process the data: {raw_data}",  # Reads from state
    output_key="processed_data"
)
```

### Shared Invocation Context

Within a single invocation:
- All sub-agents share the same `InvocationContext`
- Access same session state
- Temporary (`temp:`) namespace shared within turn

### Cross-Session Memory

```python
from google.adk.memory import VertexAiMemoryBankService

memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id="AGENT_ENGINE_ID"
)

runner = Runner(
    agent=root_agent,
    memory_service=memory_service
)
```

## Agent Communication

### 1. Local Communication (Same Process)
- Direct sub-agent invocation
- Shared memory
- Fast, in-process
- Best for tightly coupled logic

### 2. Remote Communication (A2A Protocol)
- Agent-to-Agent protocol
- Network-based
- Different processes/languages
- Best for microservices, external agents

```python
from google.adk.agents import RemoteA2aAgent

remote_agent = RemoteA2aAgent(
    name="RemoteFinanceAgent",
    url="https://finance-agent.example.com"
)

# Use as tool
coordinator = LlmAgent(
    tools=[AgentTool(remote_agent)]
)
```

## Best Practices

1. **Choose the Right Agent Type**
   - LLM agents for reasoning
   - Workflow agents for deterministic processes
   - Custom agents for unique requirements

2. **Manage State Carefully**
   - Use `output_key` for sequential data flow
   - Consider state scope (session vs invocation)
   - Implement explicit state management for parallel agents

3. **Handle Errors Gracefully**
   - Implement fallback strategies
   - Use callbacks for error handling
   - Set appropriate timeouts

4. **Optimize Performance**
   - Use parallel agents for independent tasks
   - Cache expensive operations
   - Monitor agent execution time

5. **Test Systematically**
   - Unit test individual agents
   - Integration test agent workflows
   - Use ADK's built-in evaluation tools

## Example: Complete Multi-Agent System

```python
# Specialized agents
research_agent = LlmAgent(name="Researcher", tools=[google_search])
writer_agent = LlmAgent(name="Writer", output_key="draft")
editor_agent = LlmAgent(name="Editor", output_key="final")

# Parallel research phase
parallel_research = ParallelAgent(
    name="ParallelResearch",
    sub_agents=[research_agent] * 3  # Three concurrent researchers
)

# Sequential pipeline
content_pipeline = SequentialAgent(
    name="ContentPipeline",
    sub_agents=[
        parallel_research,
        writer_agent,
        editor_agent
    ]
)

# Iterative refinement
refinement_loop = LoopAgent(
    name="QualityLoop",
    sub_agents=[content_pipeline],
    max_iterations=3
)

# Root coordinator
root_agent = LlmAgent(
    name="ContentCoordinator",
    tools=[AgentTool(refinement_loop)]
)
```

