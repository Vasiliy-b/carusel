"""
Orchestration layer for multi-agent content generation workflow
"""
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent, LlmAgent
from .agents import (
    data_collector_agent,
    content_analyzer_agent,
    creative_director_agent,
    copywriter_agent,
    image_prompt_engineer_agent,
    results_manager_agent
)
from .tools import get_next_prompt_for_generation, generate_image_from_prompt, exit_image_loop
from .post_selector_tool import select_current_post, clear_post_state
from .post_saver import save_post_metadata
from .prompt_formatter import format_image_prompts
from .config import Config
from google.adk.agents import LlmAgent


# ============================================
# POST SELECTOR AGENT
# ============================================
# Selects ONE post from filtered_posts for this iteration
post_selector_agent = LlmAgent(
    name="PostSelector",
    model=Config.TEXT_MODEL,
    include_contents='none',
    instruction="""
    Call select_current_post tool to get the next post to process.
    Confirm which post was selected and its details.
    """,
    tools=[select_current_post],
    description="Selects one post at a time from filtered_posts array",
    output_key="post_selection"
)

# ============================================
# STATE CLEANER AGENT
# ============================================
# Clears state after post processing completes
state_cleaner_agent = LlmAgent(
    name="StateCleaner",
    model=Config.TEXT_MODEL,
    include_contents='none',
    instruction="""
    Call clear_post_state tool to clean up after this post.
    This prepares state for the next post iteration.
    """,
    tools=[clear_post_state],
    description="Clears post-specific state between iterations"
)

# ============================================
# IMAGE GENERATOR AGENT (Single instance for LoopAgent)
# ============================================
# This agent uses gemini-2.5-flash for REASONING
# and calls gemini-2.5-flash-image via a TOOL for actual image generation
single_image_generator = LlmAgent(
    name="ImageGenerator",
    model=Config.TEXT_MODEL,  # gemini-2.5-flash for reasoning
    include_contents='none',
    instruction="""
    CRITICAL: You MUST call tools to actually generate images!
    
    1. CALL get_next_prompt_for_generation (no arguments)
    
    2. If status='complete':
       CALL exit_image_loop to terminate the loop
       
    3. If status='ready':
       CALL generate_image_from_prompt with prompt_text and image_text
       Confirm creation
    
    ALWAYS call tools - don't just describe what to do!
    """,
    tools=[get_next_prompt_for_generation, generate_image_from_prompt, exit_image_loop],
    description="Generates one carousel image per iteration, exits when all 10 done",
    output_key="temp:current_image"
)

# ============================================
# IMAGE COLLECTION LOOP
# ============================================
# Uses LoopAgent to generate images one at a time (10 iterations)
# This is ADK's recommended pattern for processing arrays
image_generation_loop = LoopAgent(
    name="ImageGenerationLoop",
    sub_agents=[single_image_generator],
    max_iterations=Config.CAROUSEL_IMAGE_COUNT,  # Generate 10 images
    description=f"Generates {Config.CAROUSEL_IMAGE_COUNT} carousel images iteratively using gemini-2.5-flash-image"
)


# ============================================
# CONTENT ANALYSIS PIPELINE
# ============================================
# Sequential: Analyze content, then get creative direction
content_analysis_pipeline = SequentialAgent(
    name="ContentAnalysisPipeline",
    sub_agents=[
        content_analyzer_agent,
        creative_director_agent
    ],
    description="Analyzes post content and provides creative direction"
)


# ============================================
# PROMPT FORMATTER AGENT
# ============================================
# Forces correct art_style and converts hex codes to natural language
prompt_formatter_agent = LlmAgent(
    name="PromptFormatter",
    model=Config.TEXT_MODEL,
    include_contents='none',
    instruction="""
    CRITICAL: Call format_image_prompts tool to fix the prompts.
    
    This tool automatically:
    1. Forces EXACT art_style from creative_brief into every prompt
    2. Converts hex codes to natural language colors
    
    Just call the tool and confirm success.
    """,
    tools=[format_image_prompts],
    description="Auto-fixes prompts to use correct art_style and natural colors"
)

# ============================================
# CONTENT GENERATION PIPELINE
# ============================================
# Sequential: Write copy, engineer prompts, then format them
content_generation_pipeline = SequentialAgent(
    name="ContentGenerationPipeline",
    sub_agents=[
        copywriter_agent,
        image_prompt_engineer_agent,
        prompt_formatter_agent  # NEW: Auto-fixes prompts
    ],
    description="Generates copy and image prompts, then formats them correctly"
)


# ============================================
# PER-POST PROCESSING PIPELINE
# ============================================
# Complete pipeline for processing ONE post
# Wrapped in Sequential to ensure proper order
post_processing_pipeline = SequentialAgent(
    name="PostProcessingPipeline",
    sub_agents=[
        post_selector_agent,            # SELECT current post from array
        content_analysis_pipeline,       # Analyze current post
        content_generation_pipeline,     # Create copy & prompts
        image_generation_loop,           # Generate 10 images
        results_manager_agent,          # Upload & save
        state_cleaner_agent             # Clear state for next post
    ],
    description="Waterfall pipeline: select→analyze→generate→save→clean (one post per iteration)"
)


# ============================================
# BATCH PROCESSOR
# ============================================
# Loop through filtered posts (limited by BATCH_SIZE)
batch_processor = LoopAgent(
    name="BatchProcessor",
    sub_agents=[post_processing_pipeline],
    max_iterations=Config.BATCH_SIZE if Config.BATCH_SIZE > 0 else 100,
    description=f"Processes top {Config.BATCH_SIZE if Config.BATCH_SIZE > 0 else 'all'} highest-engagement posts"
)


# ============================================
# ROOT COORDINATOR
# ============================================
# Top-level agent that orchestrates entire workflow
root_coordinator = SequentialAgent(
    name="ContentGeneratorCoordinator",
    sub_agents=[
        data_collector_agent,  # Fetch and filter posts
        batch_processor        # Process each post
    ],
    description="Root coordinator for multi-agent content generation system"
)


# Export root agent
root_agent = root_coordinator


# ============================================
# AGENT HIERARCHY DOCUMENTATION
# ============================================
"""
Agent Execution Flow:

1. DataCollector (gemini-2.5-flash)
   ↓ fetches & filters posts
   
2. BatchProcessor (Loop)
   ↓ for each post:
   
   2.1. ContentAnalysisPipeline (Sequential)
        - ContentAnalyzer (gemini-2.5-flash)
          ↓ analyzes content
        - CreativeDirector (gemini-2.5-flash)
          ↓ makes style decisions
   
   2.2. ContentGenerationPipeline (Sequential)
        - Copywriter (gemini-2.5-flash)
          ↓ writes header & caption
        - ImagePromptEngineer (gemini-2.5-flash)
          ↓ creates 10 image prompts
   
   2.3. ParallelImageGeneration (Parallel)
        - ImageGenerator x10 (gemini-2.5-flash-image)
          ↓ generates 10 images simultaneously
   
   2.4. ResultsManager (gemini-2.5-flash)
        ↓ uploads to GCS & updates sheet

3. Complete → Next post or finish

Total Agents: 7 unique (1 data + 5 processing + 1 manager)
Parallel Instances: 10 (image generators)
Models Used: 
  - gemini-2.5-flash: Analysis, direction, copy, prompting, management
  - gemini-2.5-flash-image: Image generation (nanobabana)
"""

