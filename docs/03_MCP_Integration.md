# Model Context Protocol (MCP) in ADK

## What is MCP?

The Model Context Protocol (MCP) is an open standard that standardizes how Large Language Models (LLMs) communicate with external applications, data sources, and tools. It acts as a universal connection mechanism.

## Architecture

MCP follows a client-server architecture:
- **MCP Server** - Exposes resources, prompts, and tools
- **MCP Client** - Consumes services (LLM host/AI agent)
- **Protocol** - Standardized communication layer

## ADK MCP Capabilities

ADK enables two workflows:

### 1. Using Existing MCP Servers
Your ADK agent acts as an MCP client to consume tools from external MCP servers.

### 2. Exposing ADK Tools via MCP Server
Build an MCP server that wraps ADK tools, making them accessible to any MCP client.

## MCP Toolbox for Databases

Google's open-source MCP server for securely exposing backend data sources.

### Supported Data Sources

#### Google Cloud
- **BigQuery** - SQL execution, schema discovery, AI forecasting
- **AlloyDB** - PostgreSQL-compatible with natural language queries
- **Spanner** - GoogleSQL and PostgreSQL dialects
- **Cloud SQL** - PostgreSQL, MySQL, SQL Server
- **Firestore** - NoSQL document database
- **Bigtable** - Wide-column NoSQL
- **Dataplex** - Data discovery and metadata

#### Relational & SQL
- PostgreSQL, MySQL, SQL Server (generic)
- ClickHouse, TiDB, OceanBase, Firebird, SQLite, YugabyteDB

#### NoSQL & Key-Value
- MongoDB, Couchbase, Redis, Valkey, Cassandra

#### Graph Databases
- Neo4j (Cypher queries), Dgraph

#### Data Platforms
- Looker, Trino (federated queries)

#### Other
- HTTP

### Example: Using MCP Toolbox

```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tools import MCPToolset

# Connect to MCP Toolbox
mcp_toolset = MCPToolset(
    server_uri="mcp://localhost:8000",  # MCP Toolbox server
    tools=["bigquery_query", "bigquery_schema"]
)

# Create agent with MCP tools
data_agent = LlmAgent(
    name="DataAnalyst",
    model="gemini-2.5-flash",
    instruction="You analyze data using BigQuery",
    tools=mcp_toolset.get_tools()
)
```

## FastMCP Integration

FastMCP handles MCP protocol complexity, allowing you to focus on building tools.

### Example: Creating MCP Server with FastMCP

```python
from fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("My ADK Tools")

@mcp.tool()
def calculate_sum(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def get_user_data(user_id: str) -> dict:
    """Fetch user data from database"""
    # Your implementation
    return {"user_id": user_id, "name": "John"}

# Deploy to Cloud Run
# The server exposes these tools via MCP protocol
```

### Using FastMCP Server in ADK

```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tools import MCPClient

# Connect to your FastMCP server
mcp_client = MCPClient(
    server_url="https://your-mcp-server.run.app"
)

agent = LlmAgent(
    name="MCPAgent",
    model="gemini-2.5-flash",
    tools=mcp_client.get_tools()  # Auto-discovers tools from MCP server
)
```

## MCP Servers for Genmedia

Google Cloud's MCP servers for generative media services:
- **Imagen** - Image generation
- **Veo** - Video generation  
- **Chirp 3 HD** - Voice synthesis
- **Lyria** - Music generation

```python
from google.adk.tools.mcp_tools import MCPToolset

genmedia_tools = MCPToolset(
    server_uri="mcp://genmedia.googleapis.com",
    tools=["generate_image", "generate_video", "synthesize_voice"]
)

creative_agent = LlmAgent(
    name="CreativeAgent",
    tools=genmedia_tools.get_tools()
)
```

## Using MCP Tools in ADK

### Pattern 1: Direct MCP Server Connection

```python
from google.adk.tools.mcp_tools import MCPToolset

# Connect to external MCP server
external_mcp = MCPToolset(
    server_uri="mcp://external-service.com",
    auth_token="YOUR_TOKEN"  # If required
)

agent = LlmAgent(
    name="IntegratedAgent",
    tools=external_mcp.get_tools()
)
```

### Pattern 2: Multiple MCP Sources

```python
# Combine tools from multiple MCP servers
database_tools = MCPToolset(server_uri="mcp://db-server")
api_tools = MCPToolset(server_uri="mcp://api-server")
genmedia_tools = MCPToolset(server_uri="mcp://genmedia-server")

all_tools = (
    database_tools.get_tools() +
    api_tools.get_tools() +
    genmedia_tools.get_tools()
)

agent = LlmAgent(
    name="SuperAgent",
    tools=all_tools
)
```

### Pattern 3: Custom MCP Tool Wrapper

```python
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext

class CustomMCPTool(BaseTool):
    def __init__(self, mcp_server_uri: str):
        self.mcp_client = MCPClient(server_uri=mcp_server_uri)
        
    async def run_async(self, tool_context: ToolContext, **kwargs):
        # Custom logic before MCP call
        result = await self.mcp_client.call_tool("tool_name", kwargs)
        # Custom logic after MCP call
        return result

custom_tool = CustomMCPTool("mcp://my-server")
```

## Deploying MCP Servers

### Option 1: Cloud Run

```bash
# Create Dockerfile for FastMCP server
FROM python:3.11-slim
COPY server.py .
RUN pip install fastmcp google-adk
CMD ["python", "server.py"]

# Deploy
gcloud run deploy mcp-server \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Option 2: Local Development

```bash
# Run MCP server locally
python mcp_server.py --port 8000

# Connect ADK agent
export MCP_SERVER_URI="mcp://localhost:8000"
adk web
```

### Option 3: MCP Toolbox Deployment

```bash
# Deploy MCP Toolbox for databases
git clone https://github.com/googleapis/genai-toolbox
cd genai-toolbox

# Configure data sources in config.yaml
# Deploy to Cloud Run
./deploy.sh
```

## Security & Authentication

### MCP Server Authentication

```python
mcp_toolset = MCPToolset(
    server_uri="mcp://secure-server.com",
    auth_type="bearer",
    auth_token="YOUR_TOKEN"
)
```

### Service Account for Data Access

```python
from google.adk.tools.google_cloud.mcp_toolbox import MCPToolboxConnector

connector = MCPToolboxConnector(
    project_id="PROJECT_ID",
    location="LOCATION",
    service_account_json=SERVICE_ACCOUNT_KEY
)
```

## Best Practices

1. **Use MCP for External Services**
   - Third-party APIs
   - Microservices architecture
   - Cross-team integrations

2. **Version Your MCP Servers**
   - Implement API versioning
   - Maintain backward compatibility
   - Document tool schemas

3. **Monitor MCP Connections**
   - Log all MCP calls
   - Track performance metrics
   - Implement circuit breakers

4. **Secure MCP Endpoints**
   - Use authentication
   - Validate inputs
   - Rate limit requests

5. **Cache MCP Responses**
   - Reduce redundant calls
   - Improve performance
   - Manage costs

## Troubleshooting

### Connection Issues
```python
# Test MCP connection
from google.adk.tools.mcp_tools import MCPClient

try:
    client = MCPClient(server_uri="mcp://your-server")
    tools = client.list_tools()
    print(f"Available tools: {tools}")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Tool Discovery
```python
# List all available tools from MCP server
mcp_tools = MCPToolset(server_uri="mcp://server")
for tool in mcp_tools.list_tools():
    print(f"Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Schema: {tool.schema}")
```

## Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/introduction)
- [MCP Toolbox Documentation](https://googleapis.github.io/genai-toolbox/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [MCP Servers for Genmedia](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/main/experiments/mcp-genmedia)

