"""
Orchestration layer for multi-agent content generation workflow
"""
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent, LlmAgent
from .agents import (
    text_input_processor_agent,
    data_collector_agent,
    content_analyzer_agent,
    creative_director_agent,
    copywriter_agent,
    image_prompt_engineer_agent,
    results_manager_agent
)
from .tools import get_next_prompt_for_generation, generate_image_from_prompt, exit_image_loop, generate_all_images_parallel
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
# PARALLEL IMAGE GENERATOR AGENT
# ============================================
# Generates all 10 images concurrently using async API calls
parallel_image_generator = LlmAgent(
    name="ParallelImageGenerator",
    model=Config.TEXT_MODEL,
    include_contents='none',
    instruction="""
    You will generate all 10 carousel images in parallel for maximum speed.
    
    CRITICAL: Call generate_all_images_parallel tool (no arguments needed).
    
    This tool:
    - Reads image_prompts array from state
    - Reads generation_reference_images from state (if present)
    - Generates all 10 images concurrently using async API calls
    - Saves images locally with proper naming
    
    Confirm when all images are generated successfully and report the results.
    """,
    tools=[generate_all_images_parallel],
    description="Generates all 10 carousel images in parallel using concurrent API calls"
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
# INPUT MODE ROUTER & ROOT AGENT FACTORY
# ============================================
def create_root_agent_for_mode(input_mode: str):
    """
    Create appropriate root agent based on input mode.
    Uses agent.clone() to create fresh copies that can be reused.
    
    Args:
        input_mode: 'sheet' or 'text'
    
    Returns:
        Configured root coordinator agent
    """
    # For text mode, we only process 1 post, so max_iterations=1
    # For sheet mode, respect BATCH_SIZE config
    max_iter = 1 if input_mode == 'text' else (Config.BATCH_SIZE if Config.BATCH_SIZE > 0 else 100)
    
    # Clone all agents to create fresh instances without parent conflicts
    # ADK 1.6.1+ supports agent.clone(update={}) for reusing agents across workflows
    
    # Create fresh analysis pipeline with cloned agents
    fresh_analysis_pipeline = SequentialAgent(
        name="ContentAnalysisPipeline",
        sub_agents=[
            content_analyzer_agent.clone(),
            creative_director_agent.clone()
        ],
        description="Analyzes post content and provides creative direction"
    )
    
    # Create fresh generation pipeline with cloned agents
    fresh_generation_pipeline = SequentialAgent(
        name="ContentGenerationPipeline",
        sub_agents=[
            copywriter_agent.clone(),
            image_prompt_engineer_agent.clone(),
            prompt_formatter_agent.clone()
        ],
        description="Generates copy and image prompts, then formats them correctly"
    )
    
    # Create fresh post processing pipeline with cloned agents
    fresh_post_pipeline = SequentialAgent(
        name="PostProcessingPipeline",
        sub_agents=[
            post_selector_agent.clone(),
            fresh_analysis_pipeline,
            fresh_generation_pipeline,
            parallel_image_generator.clone(),
            results_manager_agent.clone(),
            state_cleaner_agent.clone()
        ],
        description="Waterfall pipeline: select→analyze→generate→save→clean"
    )
    
    # Create fresh batch processor with mode-specific iterations
    batch_processor = LoopAgent(
        name="BatchProcessor",
        sub_agents=[fresh_post_pipeline],
        max_iterations=max_iter,
        description=f"Processes {max_iter} post(s)"
    )
    
    if input_mode == 'text':
        # Text input mode
        return SequentialAgent(
            name="TextModeCoordinator",
            sub_agents=[
                text_input_processor_agent.clone(),
                batch_processor
            ],
            description="Root coordinator for text input mode"
        )
    else:
        # Sheet mode
        return SequentialAgent(
            name="SheetModeCoordinator",
            sub_agents=[
                data_collector_agent.clone(),
                batch_processor
            ],
            description="Root coordinator for sheet input mode"
        )


# ============================================
# ROOT AGENT - Export factory function
# ============================================
# Export the factory function for dynamic creation
# Don't create instances at module level to avoid parent conflicts


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

