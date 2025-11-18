"""
Helper tool to format image prompts with correct art_style and natural language colors.
"""
import logging
import re
import json
from typing import Dict, Any, List
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def hex_to_natural_color(hex_code: str) -> str:
    """
    Convert hex color code to natural language color name.
    """
    hex_code = hex_code.strip().upper()
    
    # Common color mappings (expand as needed)
    color_map = {
        # Reds/Pinks
        "#FF0000": "bright red",
        "#8B0000": "deep crimson red",
        "#DC143C": "vibrant crimson",
        "#FFC0CB": "soft pink",
        "#FFB5B5": "light coral pink",
        "#F7A8B7": "soft rose pink",
        "#F7CAC9": "pale blush pink",
        
        # Oranges/Peaches
        "#FF8C00": "burning amber orange",
        "#FFA500": "warm orange",
        "#FFD700": "bright golden yellow",
        "#FFE5EC": "soft blush pink",
        "#FFD4B2": "peachy cream",
        "#FFC7B2": "peachy coral",
        "#FFE0B5": "delicate cream",
        
        # Yellows/Creams
        "#FDF0D5": "warm cream",
        "#F0EAD6": "soft cream",
        "#E8D5B5": "warm beige",
        
        # Browns/Tans
        "#D6AE8D": "warm sandy beige",
        "#8C5E58": "dusty rose brown",
        "#A56A6A": "muted mauve brown",
        
        # Purples/Lavenders
        "#E0BBE4": "pale lavender",
        "#957DAD": "muted purple",
        "#E5D4ED": "warm lavender",
        "#B0656F": "dusty mauve",
        "#4A3C4D": "deep plum",
        
        # Blues
        "#A9DEF9": "soft sky blue",
        "#B6CBE0": "pale blue",
        
        # Greens
        "#D0F4DE": "soft mint green",
        
        # Pinks (additional)
        "#F3D7D7": "pale dusty rose",
    }
    
    if hex_code in color_map:
        return color_map[hex_code]
    
    # Fallback: try to guess from RGB values
    try:
        hex_clean = hex_code.replace("#", "")
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        
        # Simple heuristics
        brightness = (r + g + b) / 3
        
        if brightness > 200:
            prefix = "pale"
        elif brightness > 150:
            prefix = "soft"
        elif brightness > 100:
            prefix = "muted"
        else:
            prefix = "deep"
        
        if r > g and r > b:
            if g > b:
                return f"{prefix} coral"
            else:
                return f"{prefix} rose"
        elif g > r and g > b:
            return f"{prefix} green"
        elif b > r and b > g:
            return f"{prefix} blue"
        elif r > 150 and g > 150:
            return f"{prefix} cream"
        else:
            return f"{prefix} neutral"
            
    except Exception as e:
        logger.warning(f"Could not parse hex code {hex_code}: {e}")
        return "neutral"


def format_image_prompts(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Reads creative_brief and image_prompts from state,
    ensures prompts start with the EXACT art_style from creative_brief,
    and converts all hex codes to natural language colors.
    
    Returns formatted prompts ready for image generation.
    """
    try:
        # Read from state
        creative_brief_raw = tool_context.state.get('creative_brief', '')
        image_prompts_raw = tool_context.state.get('image_prompts', '')
        
        if not creative_brief_raw or not image_prompts_raw:
            return {
                "status": "error",
                "error": "Missing creative_brief or image_prompts in state"
            }
        
        # Parse JSONs
        creative_brief = {}
        if isinstance(creative_brief_raw, str):
            try:
                clean_str = creative_brief_raw.strip()
                if clean_str.startswith('```json'):
                    clean_str = clean_str[7:]
                if clean_str.startswith('```'):
                    clean_str = clean_str[3:]
                if clean_str.endswith('```'):
                    clean_str = clean_str[:-3]
                creative_brief = json.loads(clean_str.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse creative_brief: {e}")
                return {"status": "error", "error": f"Invalid creative_brief JSON: {e}"}
        
        image_prompts = []
        if isinstance(image_prompts_raw, str):
            try:
                clean_str = image_prompts_raw.strip()
                if clean_str.startswith('```json'):
                    clean_str = clean_str[7:]
                if clean_str.startswith('```'):
                    clean_str = clean_str[3:]
                if clean_str.endswith('```'):
                    clean_str = clean_str[:-3]
                image_prompts = json.loads(clean_str.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse image_prompts: {e}")
                return {"status": "error", "error": f"Invalid image_prompts JSON: {e}"}
        
        # Check if style reference is being used
        has_style_reference = creative_brief.get('has_style_reference', False)
        
        if has_style_reference:
            # Style reference mode: Don't enforce art_style/colors, just pass through
            logger.info("Style reference detected - skipping art_style enforcement")
            
            # Just store prompts as-is (they were written for reference image)
            tool_context.state['image_prompts'] = json.dumps(image_prompts)
            
            logger.info(f"✅ Passed through {len(image_prompts)} prompts for style reference mode")
            logger.info(f"   Style will be controlled by uploaded reference image")
            
            return {
                "status": "success",
                "prompts_fixed": len(image_prompts),
                "mode": "style_reference",
                "art_style_applied": "N/A - using reference image"
            }
        
        # Normal mode: Enforce art_style and convert colors
        art_style = creative_brief.get('art_style', '')
        colors = creative_brief.get('colors', [])
        
        if not art_style:
            logger.warning("No art_style in creative_brief and no style reference")
            return {"status": "error", "error": "No art_style in creative_brief"}
        
        # Convert hex codes to natural language
        natural_colors = [hex_to_natural_color(c) for c in colors]
        
        # Fix each prompt
        fixed_prompts = []
        for prompt_data in image_prompts:
            original_prompt = prompt_data.get('p', '')
            
            # Replace hex codes with natural language
            fixed_prompt = original_prompt
            for hex_code, natural_color in zip(colors, natural_colors):
                fixed_prompt = fixed_prompt.replace(hex_code, natural_color)
            
            # Ensure prompt starts with art_style
            if not fixed_prompt.lower().startswith('create'):
                fixed_prompt = f"Create {art_style}, {fixed_prompt}"
            else:
                # Replace whatever comes after "Create " with the correct art_style
                fixed_prompt = re.sub(
                    r'^Create\s+[^,]+,',
                    f'Create {art_style},',
                    fixed_prompt,
                    flags=re.IGNORECASE
                )
            
            fixed_prompts.append({
                "i": prompt_data.get('i'),
                "t": prompt_data.get('t'),
                "p": fixed_prompt
            })
        
        # Store back in state
        tool_context.state['image_prompts'] = json.dumps(fixed_prompts)
        
        logger.info(f"✅ Formatted {len(fixed_prompts)} prompts with correct art_style and natural colors")
        logger.info(f"   Art style: '{art_style}'")
        logger.info(f"   Colors: {colors} → {natural_colors}")
        
        return {
            "status": "success",
            "prompts_fixed": len(fixed_prompts),
            "art_style_applied": art_style,
            "colors_converted": len(colors)
        }
        
    except Exception as e:
        logger.error(f"Error formatting prompts: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

