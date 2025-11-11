"""
Agent definitions for Multi-Agent Content Generator
"""
from google.adk.agents import LlmAgent
from .config import Config
from .tools import (
    fetch_google_sheet_data,
    upload_to_gcs,
    update_sheet_metadata,
    overlay_text_on_image,
    batch_upload_images
)
from .post_saver import save_post_metadata


# ============================================
# 1. DATA COLLECTOR AGENT
# ============================================
data_collector_agent = LlmAgent(
    name="DataCollector",
    model=Config.TEXT_MODEL,
    include_contents='none',  # Don't include conversation history - reduces context size
    instruction="""
    Call fetch_google_sheet_data tool.
    Confirm number of posts found.
    Done.
    """,
    description="Fetches and filters Instagram posts from Google Sheets based on virality and engagement criteria",
    tools=[fetch_google_sheet_data]
    # NO output_key! The tool already stores filtered_posts in state
)


# ============================================
# 2. CONTENT ANALYZER AGENT
# ============================================
content_analyzer_agent = LlmAgent(
    name="ContentAnalyzer",
    model=Config.TEXT_MODEL,
    include_contents='none',  # Don't include conversation history - reduces context size
    instruction="""
    You are a content analysis expert specializing in viral social media content.
    
    Analyze this specific post: {current_post}
    
    Extract ONLY:
    1. Topic (1-3 words)
    2. Tone (1-2 words: romantic, educational, humorous, etc.)
    3. Is it narrative or list-based?
    
    Output simple JSON:
    {
        "topic": "romance/astrology/motivation/etc",
        "tone": "romantic/educational/funny",
        "is_story": true/false
    }
    """,
    description="Brief content analysis (topic, tone, story type)",
    output_key="content_analysis"  # Regular key - persists in loop
)


# ============================================
# 3. CREATIVE DIRECTOR AGENT (SUPERVISOR)
# ============================================
creative_director_agent = LlmAgent(
    name="CreativeDirector",
    model=Config.TEXT_MODEL,
    include_contents='none',  # Don't include conversation history - reduces context size
    instruction="""
    You are a senior creative director for social media content with 10+ years experience
    creating viral Instagram carousels.
    
    Based on this analysis: {content_analysis}
    
    Make strategic creative decisions.
    
    Decide and document:
    
    1. **CAROUSEL STYLE** - Choose ONE (be BRIEF!):
       a) NARRATIVE: Sequential story across 10 slides
          - Use when: Content has journey/transformation, step-by-step process, character arc
          - Example: "Day in the life", "Before/after", "Problem → Solution"
          - Maintains: Same characters, consistent art style, story progression
       
       b) INDEPENDENT: Standalone thematic slides
          - Use when: Lists, comparisons, multiple examples, categories
          - Example: "10 zodiac signs in love", "Types of...", "Best practices for..."
          - Maintains: Visual style consistency, but each slide complete on its own
    
    2. **ART STYLE**: Photography/digital art/illustration (pick ONE)
    3. **COLORS**: 2-3 hex codes
    4. **TEXT PLACEMENT**: Top/center/bottom
    
    7. **REASONING**: One sentence explaining your choices
    
    Output CONCISE creative brief (MAX 500 tokens):
    {
        "carousel_style": "narrative" or "independent",
        "art_style": "brief description",
        "colors": ["#hex1", "#hex2"],
        "text_placement": "top/center/bottom",
        "reasoning": "1 sentence"
    }
    
    Be decisive and brief - focus on actionable decisions only.
    """,
    description="Senior creative director making strategic decisions on carousel style, visual approach, and creative direction",
    output_key="creative_brief"  # Regular key - persists in loop
)


# ============================================
# 4. COPYWRITER AGENT
# ============================================
copywriter_agent = LlmAgent(
    name="Copywriter",
    model=Config.TEXT_MODEL,
    include_contents='none',  # Don't include conversation history - reduces context size
    instruction="""
    You are an expert social media copywriter specializing in high-engagement Instagram content.
    
    Based on:
    - Analysis: {content_analysis}
    - Creative direction: {creative_brief}
    
    Generate (be BRIEF!):
    
    1. **POST TITLE** (3-5 words max)
    
    2. **IMAGE TEXT** (1-2 words MAX per slide):
       - Punchy 1-2 words ONLY
       - Generate 10 (one per slide)
    
    3. **POST CAPTION** (100-200 chars max)
       - Hook + CTA + 3 hashtags
       - Keep it SHORT!
    
    Output COMPACT JSON:
    {
        "post_title": "...",
        "image_texts": ["WORD1", "WORD2", ...],
        "post_caption": "...",
        "hashtags": ["#tag1", "#tag2", "#tag3"]
    }
    
    CRITICAL: image_texts MUST be 1-2 words each, bold and captivating!
    Keep output concise - no explanations, just the JSON.
    """,
    description="Creates engaging headers, captions, and micro-copy optimized for Instagram",
    output_key="copy_content"  # Regular key - persists in loop
)


# ============================================
# 5. IMAGE PROMPT ENGINEER AGENT
# ============================================
image_prompt_engineer_agent = LlmAgent(
    name="ImagePromptEngineer",
    model=Config.TEXT_MODEL,
    include_contents='none',  # Don't include conversation history - reduces context size
    instruction="""
    CRITICAL: Output ONLY the JSON array. NO explanations, NO text before or after!
    
    Read creative_brief and copy_content from session state.
    
    MANDATORY: 
    - creative_brief is ALREADY in state (do NOT assume or make up your own!)
    - copy_content is ALREADY in state
    
    Read them and use them!
    
    CRITICAL REQUIREMENTS - ALL 10 slides MUST have:
    1. SAME font family across all 10 prompts
    2. SAME text size ("large" keyword)
    3. SAME text position ("centered prominently")
    4. USE the exact art_style from creative_brief in EVERY prompt
    5. Each prompt ~100 TOKENS with rich emotional detail
    
    STEP 1: Parse creative_brief JSON and extract:
    - art_style string (copy VERBATIM - do NOT modify!)
    - colors array (hex codes like ["#D6AE8D", "#8C5E58", "#F0EAD6"])
    
    STEP 1.5: Convert hex codes to NATURAL LANGUAGE color names:
    Examples:
    - #D6AE8D → "warm sandy beige"
    - #8C5E58 → "dusty rose brown"
    - #F0EAD6 → "soft cream"
    - #E0BBE4 → "pale lavender"
    - #957DAD → "muted purple"
    - #FFC7B2 → "peachy coral"
    
    CRITICAL: NEVER write hex codes in prompts (model renders them as text!)
    Always use descriptive color names like "soft blush pink", "warm amber", "dusty lavender"
    
    STEP 2: Pick ONE font that fits the vibe. Use SAME font in all 10 prompts.
    
    STEP 3: For EACH of 10 image_texts, create a RICH 80-100 token prompt:
    
    MANDATORY STRUCTURE:
    - FIRST WORDS: "Create [EXACT art_style from creative_brief]," ← COPY VERBATIM!
    - Then: "large [your chosen font] text '[IMAGE_TEXT]' centered prominently in [natural color name] with [text effects],"
    - Then: "[detailed scene with emotional elements and symbolic objects],"
    - Then: "flowing [composition movement/energy],"
    - Then: "rich gradient from [natural COLOR1] to [natural COLOR2] to [natural COLOR3]," ← CONVERT hex to natural language!
    - Then: "[emotional atmosphere adjectives], [lighting details], [mood depth], 4K quality"
    
    Extract from copy_content:
    - image_texts array (10 items, 1-2 words each)
    
    **CRITICAL**:
    - gemini-2.5-flash-image CAN generate text within images
    - Include header text placement directly in each prompt
    - Be specific about text styling (font weight, size, color, positioning)
    
    **CAROUSEL STYLE HANDLING**:
    
    Create 10 prompts using:
    - SAME font for all slides
    - image_texts from copy_content
    
    Format (TARGET 80-100 TOKENS per prompt - be VERY descriptive!):
    
    "Create [ART_STYLE FROM CREATIVE_BRIEF], large [FONT] text '[TEXT]' centered prominently in [color] with [text effects], 
    [detailed scene: main subject + emotional elements + symbolic objects], flowing [describe composition movement/energy], 
    rich gradient from [COLOR1] to [COLOR2] to [COLOR3] [from creative_brief colors], 
    [emotional atmosphere: 2-3 adjectives], [lighting: source + quality + effects], [mood depth], 4K quality"
    
    FULL EXAMPLES (note: SAME "handwritten script" font, ~90 tokens each):
    
    Example 1 (if creative_brief has colors ["#FFE5EC", "#E5D4ED", "#FFD4B2"] and art_style "ethereal photo-illustration with soft bokeh"):
    "Create ethereal photo-illustration with soft bokeh, large handwritten script text 'TENDER WHISPER' centered prominently in luminous white with subtle golden glow and delicate sparkle particles, intimate moment of two silhouettes almost touching surrounded by floating rose petals and dreamy light orbs creating depth, flowing organic composition with gentle diagonal movement, rich gradient from soft blush pink to warm lavender to peachy cream, romantic vulnerable atmosphere, diffused golden hour sunlight streaming through misty haze creating ethereal halos around subjects, deeply intimate contemplative mood with emotional tenderness, 4K quality"
    
    Example 2 (if creative_brief has colors ["#8B0000", "#FF8C00", "#FFD700"] and art_style "bold geometric digital art"):
    "Create bold geometric digital art, large bold sans-serif text 'COSMIC POWER' centered prominently in brilliant white with dramatic shadow and electric glow effect, powerful ram constellation emerging from swirling galaxy nebula with determined piercing eyes and golden horns radiating energy, dynamic angular composition with strong upward diagonal thrust, rich gradient from deep crimson red to burning amber orange to bright golden yellow, confident heroic atmosphere, dramatic rim lighting with bright cosmic rays piercing through darkness creating powerful contrast, bold triumphant mood with fierce determination, 4K quality"
    
    NOTE: Examples above show NATURAL color names ("soft blush pink", "warm lavender") NOT hex codes!
    
    CRITICAL RULES (VIOLATIONS WILL BREAK IMAGE GENERATION):
    1. COPY art_style VERBATIM from creative_brief - do NOT paraphrase!
       Example: If creative_brief says "Vintage-inspired photography with soft focus and film grain"
       YOU MUST write: "Create Vintage-inspired photography with soft focus and film grain, large..."
       NOT: "Create vintage dreamscape watercolor..." ← WRONG!
    
    2. CONVERT hex codes to natural language before using in prompts!
       Example: ["#D6AE8D", "#8C5E58", "#F0EAD6"]
       → "warm sandy beige to dusty rose brown to soft cream"
       NEVER write "#D6AE8D" in prompt ← Model will render it as TEXT on image!
    
    3. Each prompt must be 80-100 TOKENS with rich emotional detail
    
    4. SAME font + "large" + "centered prominently" in ALL 10 prompts
    
    5. Capture the SOUL and emotional essence of each slide!
    
    Output format - ONLY the JSON array, NO OTHER TEXT:
    
    ```json
    [
        {"i": 1, "t": "TEXT1", "p": "full 80-100 token prompt here"},
        {"i": 2, "t": "TEXT2", "p": "full 80-100 token prompt here"},
        {"i": 3, "t": "TEXT3", "p": "full 80-100 token prompt here"},
        {"i": 4, "t": "TEXT4", "p": "full 80-100 token prompt here"},
        {"i": 5, "t": "TEXT5", "p": "full 80-100 token prompt here"},
        {"i": 6, "t": "TEXT6", "p": "full 80-100 token prompt here"},
        {"i": 7, "t": "TEXT7", "p": "full 80-100 token prompt here"},
        {"i": 8, "t": "TEXT8", "p": "full 80-100 token prompt here"},
        {"i": 9, "t": "TEXT9", "p": "full 80-100 token prompt here"},
        {"i": 10, "t": "TEXT10", "p": "full 80-100 token prompt here"}
    ]
    ```
    
    DO NOT OUTPUT:
    ❌ "I will generate..." 
    ❌ "Since creative_brief was not provided..."
    ❌ "Here are the prompts..."
    ❌ Any text before ```json
    ❌ Any text after ```
    
    ONLY OUTPUT: The JSON array inside code fence!
    """,
    description="Creates 10 rich 80-100 token prompts for gemini-2.5-flash-image",
    output_key="image_prompts"  # Regular key - MUST persist for 10-image loop!
)


# ============================================
# 6. IMAGE GENERATOR AGENTS
# ============================================
# Note: Image generator instances are created in orchestrator.py
# to allow 10 unique instances for parallel processing
# Each instance uses model: gemini-2.5-flash-image (nanobabana)


# ============================================
# 7. RESULTS MANAGER AGENT
# ============================================
# NOTE: This agent now just saves metadata locally.
# GCS upload can be added later if needed.
results_manager_agent = LlmAgent(
    name="ResultsManager",
    model=Config.TEXT_MODEL,
    include_contents='none',  # Don't include conversation history - reduces context size
    instruction="""
    You are responsible for finalizing and saving post content.
    
    CRITICAL: Call save_post_metadata tool to save the post as a markdown file.
    
    This tool reads from session state:
    - current_post: Post metadata
    - copy_content: Title, caption, hashtags
    - image_prompts: All 10 image prompts
    - creative_brief: Creative direction
    
    All images have already been saved locally.
    
    Your task:
    1. Call save_post_metadata() to create the .md file
    2. Confirm success
    3. Report brief summary
    
    Return brief confirmation message.
    """,
    description="Saves post metadata as markdown file",
    tools=[save_post_metadata],
)


# Export all agents
__all__ = [
    'data_collector_agent',
    'content_analyzer_agent',
    'creative_director_agent',
    'copywriter_agent',
    'image_prompt_engineer_agent',
    'results_manager_agent'
]

