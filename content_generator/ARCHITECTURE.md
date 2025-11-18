# Content Generator - Detailed Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER / TRIGGER                               │
│              "Process all qualifying posts"                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RUNNER (ADK Runtime)                            │
│  • Manages event loop                                            │
│  • Coordinates services (Session, Memory, Artifacts)             │
│  • Processes events and commits state changes                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│         ROOT COORDINATOR (SequentialAgent)                       │
│  Orchestrates: Data Collection → Batch Processing               │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌──────────────────┐          ┌────────────────────────────┐
│ PHASE 1:         │          │ PHASE 2:                   │
│ DATA COLLECTION  │          │ BATCH PROCESSING           │
└──────────────────┘          └────────────────────────────┘
        │                                  │
        ▼                                  ▼
┌──────────────────────────┐   ┌────────────────────────────────┐
│ DataCollector            │   │ BatchProcessor (LoopAgent)     │
│ (gemini-2.5-flash)       │   │ Loops through each post        │
│                          │   │ max_iterations=100             │
│ Tools:                   │   └────────────┬───────────────────┘
│  • fetch_google_sheet    │                │
│                          │                │ For each post:
│ Filters:                 │                │
│  • VIRALITY: VIRUS,      │                ▼
│    BEST, GOOD            │   ┌────────────────────────────────┐
│  • ENGAGEMENT:           │   │ PostProcessingPipeline         │
│    BEST ER, VIRAL ER     │   │ (SequentialAgent)              │
│                          │   │                                │
│ Output:                  │   │ Sub-pipelines:                 │
│  → filtered_posts        │   │  1. Content Analysis           │
│                          │   │  2. Content Generation         │
└──────────────────────────┘   │  3. Image Generation           │
                               │  4. Results Management         │
                               └────────────┬───────────────────┘
                                            │
                    ┌───────────────────────┼──────────────────────┐
                    │                       │                      │
                    ▼                       ▼                      ▼
         ┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────┐
         │ SUB-PIPELINE 1:     │  │ SUB-PIPELINE 2:  │  │ SUB-PIPELINE 3: │
         │ ANALYSIS            │  │ GENERATION       │  │ PRODUCTION      │
         └─────────────────────┘  └──────────────────┘  └─────────────────┘
                   │                       │                      │
    ┌──────────────┴────────┐   ┌─────────┴────────┐            │
    ▼                       ▼   ▼                  ▼            ▼
┌──────────┐      ┌──────────────┐   ┌────────────┐  ┌─────────────────────┐
│ Content  │  →   │  Creative    │ → │ Copywriter │→ │ ImagePromptEngineer │
│ Analyzer │      │  Director    │   │            │  │                     │
│ (flash)  │      │  (flash)     │   │  (flash)   │  │      (flash)        │
│          │      │              │   │            │  │                     │
│ Analyzes │      │ ⭐SUPERVISOR │   │ Generates: │  │ Creates 10 prompts: │
│ themes,  │      │              │   │ • Header   │  │ • Detailed scenes   │
│ hooks,   │      │ Decides:     │   │ • Caption  │  │ • Text integration  │
│ tone     │      │ • Narrative  │   │ • Hashtags │  │ • Style guidance    │
│          │      │   OR         │   │            │  │                     │
│ Output:  │      │ • Independent│   │ Output:    │  │ Output:             │
│ analysis │      │              │   │ copy       │  │ image_prompts       │
└──────────┘      │ • Art style  │   └────────────┘  └──────────┬──────────┘
                  │ • Color      │                              │
                  │ • Tone       │                              │
                  │              │                              │
                  │ Output:      │                              │
                  │ creative_brief│                             │
                  └──────────────┘                              │
                                                                 ▼
                                                    ┌────────────────────────┐
                                                    │ ParallelImageGeneration│
                                                    │ (ParallelAgent)        │
                                                    │                        │
                                                    │ 10x Concurrent:        │
                                                    └────────┬───────────────┘
                                                             │
                ┌────────────────────────────────────────────┼────────┐
                │            │           │           │       │        │
                ▼            ▼           ▼           ▼       ▼        ▼
         ┌─────────┐  ┌─────────┐  ┌─────────┐  ... (10 total)  ┌─────────┐
         │  Image  │  │  Image  │  │  Image  │                  │  Image  │
         │Generator│  │Generator│  │Generator│                  │Generator│
         │  #1     │  │  #2     │  │  #3     │                  │  #10    │
         │         │  │         │  │         │                  │         │
         │ MODEL:  │  │ MODEL:  │  │ MODEL:  │                  │ MODEL:  │
         │ gemini- │  │ gemini- │  │ gemini- │                  │ gemini- │
         │ 2.5-    │  │ 2.5-    │  │ 2.5-    │                  │ 2.5-    │
         │ flash-  │  │ flash-  │  │ flash-  │                  │ flash-  │
         │ image   │  │ image   │  │ image   │                  │ image   │
         │         │  │         │  │         │                  │         │
         │ (nanoba │  │(nanoba  │  │(nanoba  │                  │(nanoba  │
         │  bana)  │  │ bana)   │  │ bana)   │                  │ bana)   │
         └────┬────┘  └────┬────┘  └────┬────┘                  └────┬────┘
              │            │            │                            │
              └────────────┴────────────┴────────────────────────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │ Results Manager        │
                          │ (gemini-2.5-flash)     │
                          │                        │
                          │ Tools:                 │
                          │  • batch_upload_images │
                          │                        │
                          │ Actions:               │
                          │  1. Upload to GCS      │
                          │  2. Update Sheet       │
                          │                        │
                          │ Output:                │
                          │  → upload_results      │
                          └────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ OUTPUTS                      │
                    │                              │
                    │ GCS Bucket:                  │
                    │  posts/{post_id}/            │
                    │    ├── image_1.png           │
                    │    ├── image_2.png           │
                    │    └── ... (10 images)       │
                    │                              │
                    │ Google Sheets:               │
                    │  Tab: "Generated_Content"    │
                    │    ├── generated_header      │
                    │    ├── generated_text        │
                    │    ├── gcs_folder_url        │
                    │    ├── creative_style        │
                    │    └── generation_date       │
                    └──────────────────────────────┘
```

## Data Flow Architecture

### State Management Flow

```
Session State (Shared across all agents in pipeline):

Initial State: {}

After DataCollector:
  ├── filtered_posts: [{post1}, {post2}, ...]
  └── total_posts_found: N

After ContentAnalyzer (per post):
  └── content_analysis: {topic, hook, tone, ...}

After CreativeDirector (per post):
  └── creative_brief: {style, visual_approach, colors, ...}

After Copywriter (per post):
  ├── carousel_header: "..."
  ├── post_caption: "..."
  └── copy_content: {...}

After ImagePromptEngineer (per post):
  └── image_prompts: [{prompt1}, {prompt2}, ..., {prompt10}]

After ParallelImageGeneration (per post):
  └── generated_images: [bytes1, bytes2, ..., bytes10]

After ResultsManager (per post):
  ├── gcs_urls_{post_id}: [url1, url2, ..., url10]
  └── upload_results: {status, folder_url, ...}

Temporary State (cleared after each invocation):
  ├── temp:agent_start_{agent_name}: timestamp
  ├── temp:model_call_count: N
  └── temp:tool_calls: [...]
```

## Agent Communication Patterns

### 1. Sequential Communication (via output_key)

```python
Agent1 (output_key="data") → State['data'] = result
                                     ↓
Agent2 (instruction uses {data}) ← Reads State['data']
```

### 2. Parallel Communication (independent execution)

```python
ParallelAgent spawns 10 instances:
  Instance1 → processes prompt[0] → generates image1
  Instance2 → processes prompt[1] → generates image2
  ...
  Instance10 → processes prompt[9] → generates image10
  
All results collected after completion
```

### 3. Loop Communication (iterative processing)

```python
LoopAgent (max_iterations=100):
  Iteration 1: Process post[0]
  Iteration 2: Process post[1]
  ...
  Until: All posts processed or max_iterations reached
```

## Tool Integration Architecture

```
┌────────────────────────────────────────────┐
│             CUSTOM TOOLS                   │
├────────────────────────────────────────────┤
│                                            │
│  fetch_google_sheet_data()                 │
│  ├─ Input: None (uses Config)             │
│  ├─ Process:                               │
│  │   1. GET CSV from public sheet         │
│  │   2. Parse with pandas                 │
│  │   3. Filter by VIRALITY & ENGAGEMENT   │
│  │   4. Extract relevant columns          │
│  ├─ Output: {posts: [...], total: N}      │
│  └─ State: stores filtered_posts          │
│                                            │
│  upload_to_gcs()                           │
│  ├─ Input: post_id, images[], metadata    │
│  ├─ Process:                               │
│  │   1. Init GCS client                   │
│  │   2. Create bucket if needed           │
│  │   3. Upload each image with retry      │
│  │   4. Make public (if configured)       │
│  ├─ Output: {urls: [...], folder_url}     │
│  └─ State: stores gcs_urls_{post_id}      │
│                                            │
│  update_sheet_metadata()                   │
│  ├─ Input: post_id, header, text, urls    │
│  ├─ Process:                               │
│  │   1. Authenticate with gspread         │
│  │   2. Open spreadsheet                  │
│  │   3. Create/access output tab          │
│  │   4. Append row with results           │
│  ├─ Output: {status, updated_at}          │
│  └─ Fallback: Store locally if no creds   │
│                                            │
│  overlay_text_on_image()                   │
│  ├─ Input: image_bytes, text, position    │
│  ├─ Process:                               │
│  │   1. Load image with PIL               │
│  │   2. Calculate text position           │
│  │   3. Draw outline for contrast         │
│  │   4. Draw main text                    │
│  ├─ Output: modified_image_bytes          │
│  └─ Use: Fallback if gemini fails         │
│                                            │
│  batch_upload_images()                     │
│  ├─ Input: post_data, image_data[]        │
│  ├─ Process:                               │
│  │   1. Upload all images to GCS          │
│  │   2. Update sheet with metadata        │
│  ├─ Output: {urls, folder_url, status}    │
│  └─ Combines: upload + update in one call │
└────────────────────────────────────────────┘
```

## Agent Detailed Specifications

### 1. Data Collector Agent
- **Model**: gemini-2.5-flash
- **Type**: LlmAgent
- **Tools**: fetch_google_sheet_data
- **Input**: User trigger message
- **Processing**: 
  - Calls tool to fetch from https://docs.google.com/spreadsheets/d/{id}/export?format=csv
  - Tool filters data by VIRALITY and ENGAGEMENT
  - Returns summary of posts found
- **Output Key**: filtered_posts
- **State Writes**: 
  - `filtered_posts`: Array of post dictionaries
  - `total_posts_found`: Integer count

### 2. Content Analyzer Agent
- **Model**: gemini-2.5-flash
- **Type**: LlmAgent
- **Tools**: None (pure LLM analysis)
- **Input**: Reads `{filtered_posts}` from state
- **Processing**:
  - Analyzes each post's rewrited_script
  - Extracts: topic, hook quality, narrative elements, tone, audience
  - Structures findings in JSON
- **Output Key**: content_analysis
- **State Reads**: filtered_posts
- **State Writes**: content_analysis

### 3. Creative Director Agent (SUPERVISOR)
- **Model**: gemini-2.5-flash
- **Type**: LlmAgent
- **Tools**: None (strategic reasoning)
- **Input**: Reads `{content_analysis}` from state
- **Processing**:
  - **Key Decision**: Narrative vs Independent carousel style
  - Determines visual approach (photography, illustration, etc.)
  - Selects tone/mood
  - Defines color palette
  - Plans text integration strategy
  - Suggests creative enhancements
  - Provides detailed reasoning for all decisions
- **Output Key**: creative_brief
- **State Reads**: content_analysis
- **State Writes**: creative_brief (JSON with style decision and visual strategy)
- **Unique Role**: Only agent that makes strategic creative decisions

### 4. Copywriter Agent
- **Model**: gemini-2.5-flash
- **Type**: LlmAgent
- **Tools**: None (creative writing)
- **Input**: Reads `{content_analysis}` and `{creative_brief}`
- **Processing**:
  - Generates carousel header (5-8 words, attention-grabbing)
  - Writes Instagram caption (150-300 chars with hooks and CTAs)
  - Includes 3-5 relevant hashtags
  - Creates slide-specific micro-copy if narrative style
- **Output Key**: copy_content
- **State Reads**: content_analysis, creative_brief
- **State Writes**: copy_content (JSON with header, caption, hashtags)

### 5. Image Prompt Engineer Agent
- **Model**: gemini-2.5-flash
- **Type**: LlmAgent
- **Tools**: None (prompt engineering)
- **Input**: Reads `{creative_brief}` and `{copy_content}`
- **Processing**:
  - Creates 10 detailed prompts optimized for gemini-2.5-flash-image
  - **If NARRATIVE**: Sequential story across 10 slides with progression
  - **If INDEPENDENT**: 10 thematic variations (e.g., zodiac signs)
  - Includes text overlay instructions in each prompt
  - Specifies: art style, colors, lighting, composition, mood
  - Each prompt: 200-400 characters with high specificity
- **Output Key**: image_prompts
- **State Reads**: creative_brief, copy_content
- **State Writes**: image_prompts (Array of 10 prompt objects)

### 6. Image Generator Agent (x10 instances)
- **Model**: gemini-2.5-flash-image (NANOBABANA)
- **Type**: LlmAgent
- **Tools**: None (native image generation)
- **Input**: Individual prompt from `{image_prompts}` array
- **Processing**:
  - Generates image based on detailed prompt
  - Includes text overlay as specified in prompt
  - Returns image in specified format (PNG/JPEG)
- **Output Key**: generated_image
- **Instances**: 10 running in parallel via ParallelAgent
- **Unique**: ONLY agent using gemini-2.5-flash-image model

### 7. Results Manager Agent
- **Model**: gemini-2.5-flash
- **Type**: LlmAgent
- **Tools**: batch_upload_images
- **Input**: Reads all generated images and metadata from state
- **Processing**:
  - Collects all 10 images
  - Calls batch_upload_images tool:
    - Uploads to GCS with organized structure
    - Updates Google Sheets with metadata
  - Verifies upload success
  - Generates completion report
- **Output Key**: upload_results
- **State Reads**: generated_images, carousel_header, post_caption, carousel_style
- **State Writes**: upload_results, gcs_urls_{post_id}

## Execution Flow Timeline

```
Time    Agent                       Action                      State Changes
────────────────────────────────────────────────────────────────────────────
T0      Runner                      Receives user message       session.events += [user_event]
T1      DataCollector              Calls fetch_google_sheet     filtered_posts = [...]
T2      DataCollector              Returns summary              [YIELD EVENT]
        └─ Runner commits state                                 State committed to session
        
T3      BatchProcessor (Loop)      Starts iteration 1           current_post = post[0]
        
T4      ContentAnalyzer            Analyzes post[0]             content_analysis = {...}
T5      ContentAnalyzer            Returns analysis             [YIELD EVENT]
        
T6      CreativeDirector           Makes style decision         creative_brief = {...}
T7      CreativeDirector           Returns brief                [YIELD EVENT]
        
T8      Copywriter                 Generates copy               copy_content = {...}
T9      Copywriter                 Returns copy                 [YIELD EVENT]
        
T10     ImagePromptEngineer        Creates 10 prompts           image_prompts = [...]
T11     ImagePromptEngineer        Returns prompts              [YIELD EVENT]
        
T12     ParallelImageGeneration    Spawns 10 instances          [10 PARALLEL EXECUTIONS]
        ├─ ImageGenerator #1       Generates image 1            [YIELD EVENT]
        ├─ ImageGenerator #2       Generates image 2            [YIELD EVENT]
        ├─ ImageGenerator #3       Generates image 3            [YIELD EVENT]
        ... (continues in parallel)
        └─ ImageGenerator #10      Generates image 10           [YIELD EVENT]
        └─ All complete                                         generated_images = [...]
        
T13     ResultsManager             Uploads to GCS               gcs_urls = [...]
T14     ResultsManager             Updates sheet                upload_results = {...}
T15     ResultsManager             Returns report               [YIELD EVENT]
        
T16     BatchProcessor             Iteration 1 complete         
T17     BatchProcessor             Starts iteration 2           current_post = post[1]
        ... (repeats for all posts)
        
TN      BatchProcessor             All iterations complete
TN+1    RootCoordinator            Returns final summary        [FINAL RESPONSE]
```

## Error Handling & Resilience

### Retry Strategy
```python
Tool Execution:
  Attempt 1 → Fail → Wait 2s
  Attempt 2 → Fail → Wait 4s  
  Attempt 3 → Fail → Raise exception
                 ↓
         Error logged to state
         Session continues (post marked as failed)
```

### Fallback Mechanisms
```
Image Text Overlay:
  Primary: gemini-2.5-flash-image with text in prompt
          ↓ (if text unclear/missing)
  Fallback: PIL/Pillow overlay_text_on_image
          ↓ (if still fails)
  Last Resort: Image without text + log error
```

### Monitoring Callbacks
```
before_agent_callback → Log start time
                        Track in temp state
                        
after_agent_callback  → Calculate duration
                        Update execution_times
                        Log completion
                        
before_model_callback → Count API calls
                        Check rate limits
                        
after_model_callback  → Validate response
                        Track costs
                        
before_tool_callback  → Log tool name & args
                        Validate inputs
                        
after_tool_callback   → Log results
                        Check for errors
```

## Scalability Considerations

### Concurrent Processing Limits
- **Parallel Images**: 10 simultaneous gemini-2.5-flash-image calls
- **Batch Size**: Configurable (0 = unlimited)
- **Rate Limiting**: Built into Vertex AI client
- **Timeout Handling**: 60s for images, 30s for text

### Resource Management
- **Memory**: InMemorySessionService for development
- **State Size**: Cleared temp state after each invocation
- **Logs**: Rotated, configurable level
- **Artifacts**: Stored in GCS, not in-memory

### Deployment Options
1. **Local**: Direct Python execution
2. **ADK Web UI**: Development interface
3. **Cloud Run**: Serverless deployment (future)
4. **GKE**: Kubernetes deployment (future)

## Configuration Matrix

| Setting | Development | Production |
|---------|------------|------------|
| Authentication | ADC Login | Service Account |
| Session Service | InMemory | Vertex AI (future) |
| Memory Service | None | Vertex AI Memory Bank |
| Logging | Console | File + Cloud Logging |
| Batch Size | 2-5 | 0 (unlimited) |
| Parallel Images | 5 | 10 |
| GCS Bucket | Private | Public or CDN |

## Performance Metrics

### Expected Throughput
- **Single Post**: ~30-45 seconds
  - Analysis: 5s
  - Creative Direction: 5s
  - Copy Generation: 5s
  - Prompt Engineering: 5s
  - Image Generation (parallel): 10-15s (10 images at once)
  - Upload: 5s
  
- **Batch (10 posts)**: ~5-7 minutes
- **Large Batch (100 posts)**: ~45-60 minutes

### Cost Estimation (Approximate)
- **Per Post**: 
  - Text generation: 5 API calls × gemini-2.5-flash
  - Image generation: 10 API calls × gemini-2.5-flash-image
  - GCS storage: 10 images × ~500KB = 5MB
  - Sheets API: 1-2 calls

## Security Architecture

### Credentials Management
```
.env (git-ignored) → Config class → Agents/Tools
                                      ↓
                            Never hardcoded
                            Never logged
                            Never in version control
```

### Access Control
- **GCS Bucket**: Optional public access for generated images
- **Sheets**: Public read, authenticated write
- **Service Accounts**: Minimal required permissions
- **API Keys**: Environment variables only

### Data Privacy
- **Session State**: Temporary, in-memory
- **Logs**: Configurable, PII-aware
- **Uploads**: Organized by post_id, time-stamped

## Extensibility Points

### Adding New Agents
```python
new_agent = LlmAgent(
    name="NewSpecialist",
    model=Config.TEXT_MODEL,
    instruction="...",
    tools=[...],
    output_key="new_data"
)

# Add to pipeline
extended_pipeline = SequentialAgent(
    sub_agents=[existing_pipeline, new_agent]
)
```

### Adding New Tools
```python
def new_tool(tool_context: ToolContext, param: str) -> dict:
    """Tool description"""
    # Implementation
    return {"result": "value"}

agent = LlmAgent(tools=[new_tool])
```

### Adding MCP Integrations
```python
from google.adk.tools.mcp_tools import MCPToolset

mcp_tools = MCPToolset(server_uri="mcp://service.com")
agent = LlmAgent(tools=mcp_tools.get_tools())
```

### Adding Callbacks
```python
from callbacks import add_monitoring_to_agent

monitored_agent = add_monitoring_to_agent(my_agent)
```

## Troubleshooting Decision Tree

```
Issue: No posts found
├─ Check: Sheet accessible? → Run verify_setup.py
├─ Check: Filters too strict? → Adjust VIRALITY_FILTER, ENGAGEMENT_FILTER
└─ Check: Sheet has data? → Verify INSTAGRAM tab exists

Issue: Authentication error
├─ Vertex AI → Run: gcloud auth application-default login
├─ AI Studio → Check GOOGLE_API_KEY in .env
└─ Service Account → Verify GOOGLE_APPLICATION_CREDENTIALS path

Issue: Image generation fails
├─ Check: gemini-2.5-flash-image model available in region
├─ Check: Quota limits in GCP console
├─ Enable: ENABLE_TEXT_OVERLAY_FALLBACK=TRUE
└─ Review: Image prompt length and complexity

Issue: GCS upload fails
├─ Check: Bucket exists → Run verify_setup.py
├─ Check: Permissions → Service account has Storage Admin role
└─ Create: gsutil mb gs://your-bucket-name

Issue: Sheet update fails
├─ Check: SHEETS_SERVICE_ACCOUNT_PATH configured
├─ Fallback: Results stored in state/logs
└─ Manual: Copy from logs to sheet
```

## Future Enhancements

### Potential Additions
1. **Quality Evaluation Agent**: Validates generated content quality
2. **A/B Testing Agent**: Generates variations for testing
3. **Performance Analyzer**: Predicts virality score
4. **Brand Compliance Agent**: Ensures brand guidelines
5. **Localization Agent**: Multi-language support
6. **Video Generation**: Extend to video carousels
7. **Real-time Monitoring**: Dashboard for batch progress
8. **Cost Optimizer**: Balances quality vs cost

### MCP Integration Opportunities
- **Notion MCP**: Store creative briefs
- **GitHub MCP**: Version control for prompts
- **Database MCP**: Analytics and reporting
- **Slack MCP**: Notifications on completion

## Monitoring & Observability

### Logs Generated
```
logs/content_generator.log:
  - Agent start/stop times
  - Tool executions
  - Model calls
  - Errors and warnings
  - Performance metrics
```

### State Tracking
```
session.state:
  - agent_execution_times: {agent_name: duration}
  - model_call_count: N
  - tool_calls: [{tool, agent, timestamp}, ...]
  - errors: [{agent, error, timestamp}, ...]
```

### Cost Tracking (if enabled)
```
TRACK_COSTS=TRUE:
  - Counts all model API calls
  - Estimates token usage
  - Tracks GCS storage
  - Logs to separate file
```

---

## NEW: Enhanced Input Modes (v2.0)

### Text Input Mode
- **Feature**: Users can provide free-form text instead of fetching from Google Sheets
- **Implementation**: `TextInputProcessor` agent converts text to structured post format
- **Integration**: Seamlessly integrates with existing pipeline via input mode router
- **Usage**: Web UI modal with textarea for content ideas
- **Agent**: `text_input_processor_agent` reads from `user_text_input` state

### Reference Image Styling
- **Feature**: Support for up to 2 reference images: STYLE and PERSONA
- **Images passed to**: `gemini-2.5-flash-image` with appropriate instructions
- **Style Transfer**: "Use this image as a style reference" instruction
- **Persona Preservation**: "Use the person's face and preserve all facial features" instruction
- **Storage**: Temporarily stored during generation, cleaned up after completion
- **API Documentation**: [Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)

### Parallel Image Generation
- **Improvement**: Replaced sequential LoopAgent (10 iterations) with parallel generation
- **Implementation**: `generate_all_images_parallel` tool uses asyncio for concurrent API calls
- **Performance**: ~10x faster (1-2 seconds vs 10-15 seconds)
- **Approach**: Direct async API calls wrapped in agent tool for ADK integration
- **Benefit**: Maintains agent architecture while maximizing parallel execution

### Download Feature
- **Package**: ZIP file with `post_content.txt` and all 10 images
- **Content**: Title, caption, hashtags, and slide texts
- **Location**: Available from post detail page header and sidebar
- **Format**: Images in `/images/` subfolder, content in root
- **Convenience**: One-click download for SMM team handoff

### Input Mode Router
- **Function**: `create_root_agent_for_mode(input_mode: str)`
- **Modes**: 
  - `'sheet'`: DataCollector → BatchProcessor
  - `'text'`: TextInputProcessor → BatchProcessor
- **Selection**: Environment variable `INPUT_MODE` set by Web UI
- **Flexibility**: Easy to add new input modes in the future

### Architecture Changes Summary

**New Agents**:
1. `text_input_processor_agent` - Converts free-form text to structured posts
2. `parallel_image_generator` - Replaces `image_generation_loop`

**New Tools**:
1. `process_text_input()` - Structures text input
2. `generate_all_images_parallel()` - Concurrent image generation

**Updated Agents**:
1. `image_prompt_engineer_agent` - Now handles reference image instructions
2. `root_coordinator` - Now uses input mode router

**Web UI Enhancements**:
1. Text input modal with file upload (STYLE/PERSONA images)
2. Download route (`/download/<post_id>`)
3. Generate from text route (`/generate_from_text`)
4. Dual button interface (Sheet vs Text)

**File Changes**:
- `config.py`: Added image upload and input mode settings
- `tools.py`: Added parallel generation and text processing
- `orchestrator.py`: Replaced loop with parallel agent, added router
- `agents.py`: Added text processor, updated prompt engineer
- `main.py`: Added input mode routing and reference image loading
- `web_ui/app.py`: Added upload handling, text mode, download ZIP
- `web_ui/templates/index.html`: Added modal and text button
- `web_ui/templates/post_detail.html`: Enhanced download buttons

---

**Architecture Status**: ✅ Complete and Production-Ready (v2.0)
**Last Updated**: 2025-11-17
**Version**: 2.0.0

