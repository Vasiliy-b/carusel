# ADK Tools Ecosystem

## Overview

Tools give agents capabilities beyond conversation, enabling interaction with external APIs, data sources, code execution, and other services.

## Tool Categories

### 1. Built-in Tools (Gemini Native)

#### Google Search
```python
from google.adk.tools import google_search

agent = LlmAgent(
    name="SearchAgent",
    tools=[google_search]
)
```

#### Code Execution
```python
from google.adk.tools import code_execution

agent = LlmAgent(
    name="CodeAgent",
    tools=[code_execution],
    instruction="Generate and execute Python code when needed"
)
```

### 2. Google Cloud Tools

#### BigQuery
```python
from google.adk.tools.built_in import BigQueryTool

bq_tool = BigQueryTool(
    project_id="PROJECT_ID",
    dataset_id="DATASET_ID"
)

agent = LlmAgent(tools=[bq_tool])
```

#### Bigtable
```python
from google.adk.tools.built_in import BigtableTool

bt_tool = BigtableTool(
    project_id="PROJECT_ID",
    instance_id="INSTANCE_ID"
)
```

#### Spanner
```python
from google.adk.tools.built_in import SpannerTool

spanner_tool = SpannerTool(
    project_id="PROJECT_ID",
    instance_id="INSTANCE_ID",
    database_id="DATABASE_ID"
)
```

#### Vertex AI RAG Engine
```python
from google.adk.tools.built_in import VertexRagTool

rag_tool = VertexRagTool(
    project_id="PROJECT_ID",
    location="LOCATION",
    corpus_name="CORPUS_NAME"
)
```

#### Vertex AI Search
```python
from google.adk.tools.built_in import VertexSearchTool

search_tool = VertexSearchTool(
    project_id="PROJECT_ID",
    location="LOCATION",
    data_store_id="DATA_STORE_ID"
)
```

### 3. Application Integration Tools

#### Apigee API Hub
Turn any documented API from Apigee API Hub into a tool:

```python
from google.adk.tools.apihub_tool.apihub_toolset import APIHubToolset
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

# Configure authentication
auth_scheme, auth_credential = token_to_scheme_credential(
    "apikey", "query", "apikey", "YOUR_API_KEY"
)

api_toolset = APIHubToolset(
    name="api-hub-tool",
    description="Access APIs from Apigee API Hub",
    access_token="APIGEE_ACCESS_TOKEN",
    apihub_resource_name="projects/PROJECT/locations/LOCATION/apis/API_ID",
    auth_scheme=auth_scheme,
    auth_credential=auth_credential
)

agent = LlmAgent(tools=api_toolset.get_tools())
```

#### Application Integration
Connect to 100+ enterprise systems (Salesforce, SAP, ServiceNow, etc.):

```python
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset

# Integration Connectors
connector_tool = ApplicationIntegrationToolset(
    project="PROJECT_ID",
    location="LOCATION",
    connection="CONNECTION_NAME",
    entity_operations={"Entity_One": ["LIST", "CREATE"]},
    actions=["action1"]
)

# Application Integration Workflows
integration_tool = ApplicationIntegrationToolset(
    project="PROJECT_ID",
    location="LOCATION",
    integration="INTEGRATION_NAME",
    triggers=["api_trigger/TRIGGER_NAME"]
)

agent = LlmAgent(
    tools=[connector_tool, integration_tool]
)
```

### 4. Third-Party Tools

#### Firecrawl
Web scraping and crawling:

```python
from google.adk.tools.third_party.firecrawl import FirecrawlTool

firecrawl = FirecrawlTool(api_key="FIRECRAWL_API_KEY")

agent = LlmAgent(
    tools=[firecrawl],
    instruction="Use Firecrawl to extract content from websites"
)
```

#### GitHub
Code analysis, issue management, PR automation:

```python
from google.adk.tools.third_party.github import GitHubToolset

github_tools = GitHubToolset(token="GITHUB_TOKEN")

agent = LlmAgent(
    tools=github_tools.get_tools()
)
```

#### Notion
Workspace management:

```python
from google.adk.tools.third_party.notion import NotionToolset

notion_tools = NotionToolset(
    auth_token="NOTION_INTEGRATION_TOKEN"
)

agent = LlmAgent(
    tools=notion_tools.get_tools()
)
```

#### Tavily
Real-time web search and extraction:

```python
from google.adk.tools.third_party.tavily import TavilyTool

tavily = TavilyTool(api_key="TAVILY_API_KEY")

agent = LlmAgent(
    tools=[tavily]
)
```

#### Browserbase
Cloud browser automation with Stagehand:

```python
from google.adk.tools.third_party.browserbase import BrowserbaseTool

browserbase = BrowserbaseTool(api_key="BROWSERBASE_API_KEY")
```

#### Exa
Search for code, technical examples, and live data:

```python
from google.adk.tools.third_party.exa import ExaTool

exa = ExaTool(api_key="EXA_API_KEY")
```

#### Hugging Face
Access models, datasets, and research papers:

```python
from google.adk.tools.third_party.hugging_face import HuggingFaceTool

hf = HuggingFaceTool(api_token="HF_TOKEN")
```

### 5. Custom Function Tools

Create your own tools from Python functions:

```python
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

def calculate_roi(tool_context: ToolContext, investment: float, return_value: float) -> dict:
    """Calculate return on investment percentage.
    
    Args:
        investment: Initial investment amount
        return_value: Final return value
        
    Returns:
        Dictionary with ROI percentage
    """
    roi = ((return_value - investment) / investment) * 100
    return {"roi_percentage": roi}

roi_tool = FunctionTool(calculate_roi)

agent = LlmAgent(
    name="FinanceAgent",
    tools=[roi_tool]
)
```

#### Async Function Tools

```python
import asyncio

async def fetch_stock_price(
    tool_context: ToolContext,
    symbol: str
) -> dict:
    """Fetch current stock price (async)"""
    # Simulate API call
    await asyncio.sleep(1)
    return {"symbol": symbol, "price": 150.25}

stock_tool = FunctionTool(fetch_stock_price)
```

#### Tool with State Management

```python
def update_counter(tool_context: ToolContext, increment: int = 1) -> dict:
    """Increment a counter stored in state"""
    current = tool_context.state.get('counter', 0)
    new_value = current + increment
    tool_context.state['counter'] = new_value
    return {"counter": new_value}

counter_tool = FunctionTool(update_counter)
```

### 6. MCP Tools

Integrate with any MCP server:

```python
from google.adk.tools.mcp_tools import MCPToolset

mcp_tools = MCPToolset(
    server_uri="mcp://external-service.com",
    auth_token="TOKEN"
)

agent = LlmAgent(
    tools=mcp_tools.get_tools()
)
```

### 7. OpenAPI Tools

Generate tools from OpenAPI specifications:

```python
from google.adk.tools.openapi_tool.openapi_toolset import OpenAPIToolset

api_tools = OpenAPIToolset(
    name="PetStore",
    openapi_spec_url="https://petstore.swagger.io/v2/swagger.json",
    operations=["findPetsByStatus", "addPet"]
)

agent = LlmAgent(
    tools=api_tools.get_tools()
)
```

### 8. LangChain Tools

Integrate LangChain tools:

```python
from langchain_community.tools.tavily_search import TavilySearchResults
from google.adk.tools.langchain_tool import LangChainTool

tavily_search = TavilySearchResults(max_results=5)
adk_tavily_tool = LangChainTool(tavily_search)

agent = LlmAgent(
    tools=[adk_tavily_tool]
)
```

### 9. CrewAI Tools

Integrate CrewAI tools:

```python
from crewai_tools import FileReadTool
from google.adk.tools.crewai_tool import CrewAITool

file_read = FileReadTool()
adk_file_tool = CrewAITool(file_read)

agent = LlmAgent(
    tools=[adk_file_tool]
)
```

## Tool Authentication

### API Key Authentication

```python
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

auth_scheme, auth_credential = token_to_scheme_credential(
    auth_type="apikey",
    location="header",  # or "query"
    key_name="X-API-Key",
    credential_value="YOUR_API_KEY"
)

tool = OpenAPIToolset(
    openapi_spec_url="...",
    auth_scheme=auth_scheme,
    auth_credential=auth_credential
)
```

### Bearer Token

```python
auth_scheme, auth_credential = token_to_scheme_credential(
    auth_type="bearer",
    location="header",
    key_name="Authorization",
    credential_value="YOUR_BEARER_TOKEN"
)
```

### OAuth2

```python
from google.adk.tools.openapi_tool.auth.auth_helpers import dict_to_auth_scheme
from google.adk.auth import AuthCredential, OAuth2Auth

oauth2_scheme = {
    "type": "oauth2",
    "flows": {
        "authorizationCode": {
            "authorizationUrl": "https://accounts.google.com/o/oauth2/auth",
            "tokenUrl": "https://oauth2.googleapis.com/token",
            "scopes": {
                "https://www.googleapis.com/auth/userinfo.email": "Email access"
            }
        }
    }
}

auth_scheme = dict_to_auth_scheme(oauth2_scheme)
auth_credential = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    oauth2=OAuth2Auth(
        client_id="CLIENT_ID",
        client_secret="CLIENT_SECRET"
    )
)
```

## Tool Performance Optimization

### Parallel Tool Execution

```python
# Define tools as async functions for parallel execution
async def tool1(tool_context: ToolContext) -> dict:
    await asyncio.sleep(1)
    return {"result": "tool1"}

async def tool2(tool_context: ToolContext) -> dict:
    await asyncio.sleep(1)
    return {"result": "tool2"}

# Agent will execute these in parallel when possible
agent = LlmAgent(
    tools=[FunctionTool(tool1), FunctionTool(tool2)]
)
```

### Tool Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_computation(tool_context: ToolContext, input_data: str) -> dict:
    """Cached tool - results stored for repeated calls"""
    # Expensive operation
    result = complex_calculation(input_data)
    return {"result": result}
```

## Action Confirmations

Request user approval before executing tools:

```python
from google.adk.tools.tool_context import ToolContext

def sensitive_operation(tool_context: ToolContext, data: str) -> dict:
    """Delete user data - requires confirmation"""
    
    # Request confirmation
    tool_context.actions.require_confirmation = True
    tool_context.actions.confirmation_prompt = (
        f"Are you sure you want to delete: {data}?"
    )
    
    # Operation only executes if user confirms
    delete_data(data)
    return {"status": "deleted"}
```

## Best Practices

1. **Tool Selection**
   - Use built-in tools when available
   - Create custom tools for specific needs
   - Integrate third-party tools for specialized functionality

2. **Tool Design**
   - Clear, descriptive names
   - Comprehensive docstrings
   - Type hints for parameters
   - Structured return values (dicts)

3. **Error Handling**
   - Validate inputs
   - Handle exceptions gracefully
   - Return informative error messages

4. **Security**
   - Store credentials securely (Secret Manager)
   - Validate tool inputs
   - Use confirmation for sensitive operations
   - Rate limit expensive tools

5. **Performance**
   - Use async tools for I/O operations
   - Implement caching where appropriate
   - Enable parallel execution
   - Monitor tool execution times

6. **Testing**
   - Unit test tool functions
   - Mock external dependencies
   - Test error scenarios
   - Validate return schemas

## Example: Multi-Tool Agent

```python
from google.adk.agents import LlmAgent
from google.adk.tools import (
    google_search,
    code_execution,
    FunctionTool
)
from google.adk.tools.third_party.firecrawl import FirecrawlTool

# Custom tool
def analyze_sentiment(tool_context: ToolContext, text: str) -> dict:
    """Analyze sentiment of text"""
    # Your ML model here
    return {"sentiment": "positive", "confidence": 0.95}

# Combine multiple tool types
research_agent = LlmAgent(
    name="ResearchAgent",
    model="gemini-2.5-flash",
    instruction="Research topics using all available tools",
    tools=[
        google_search,              # Built-in
        code_execution,             # Built-in
        FirecrawlTool(),           # Third-party
        FunctionTool(analyze_sentiment)  # Custom
    ]
)
```

