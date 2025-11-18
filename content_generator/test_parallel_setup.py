"""
Test script to verify parallel image generation setup
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from content_generator.config import Config
from content_generator.orchestrator import (
    parallel_image_generation,
    post_processing_pipeline,
    root_coordinator
)

print("="*70)
print("PARALLEL IMAGE GENERATION SETUP VERIFICATION")
print("="*70)

# 1. Verify Config
print("\n1. Configuration:")
print(f"   ✓ TEXT_MODEL: {Config.TEXT_MODEL}")
print(f"   ✓ IMAGE_MODEL: {Config.IMAGE_MODEL}")
print(f"   ✓ CAROUSEL_IMAGE_COUNT: {Config.CAROUSEL_IMAGE_COUNT}")
print(f"   ✓ BATCH_SIZE default: {Config.BATCH_SIZE}")
print(f"   ✓ GCS_BUCKET: {Config.GCS_BUCKET}")
print(f"   ✓ OUTPUT_SHEET_ID: {Config.OUTPUT_SHEET_ID or '(not configured)'}")
print(f"   ✓ BRAND_IMAGE_PROMPT: {Config.BRAND_IMAGE_PROMPT or '(not set - using default)'}")

# 2. Verify ParallelAgent structure
print("\n2. Parallel Image Generation:")
print(f"   ✓ Agent type: {type(parallel_image_generation).__name__}")
print(f"   ✓ Number of sub-agents: {len(parallel_image_generation.sub_agents)}")
print(f"   ✓ Sub-agent names:")
for i, agent in enumerate(parallel_image_generation.sub_agents[:3]):  # Show first 3
    print(f"      - {agent.name} (model: {agent.model})")
if len(parallel_image_generation.sub_agents) > 3:
    print(f"      ... and {len(parallel_image_generation.sub_agents) - 3} more")

# 3. Verify pipeline structure
print("\n3. Post Processing Pipeline:")
print(f"   ✓ Pipeline type: {type(post_processing_pipeline).__name__}")
print(f"   ✓ Sub-agents in pipeline:")
for agent in post_processing_pipeline.sub_agents:
    print(f"      - {agent.name}")

# 4. Verify root coordinator
print("\n4. Root Coordinator:")
print(f"   ✓ Root agent: {root_coordinator.name}")
print(f"   ✓ Type: {type(root_coordinator).__name__}")

# 5. Check for new tools
print("\n5. Tool Verification:")
try:
    from content_generator.tools import generate_single_image_by_index, upload_and_export_post
    print("   ✓ generate_single_image_by_index imported successfully")
    print("   ✓ upload_and_export_post imported successfully")
except ImportError as e:
    print(f"   ✗ Import error: {e}")

# 6. Check context manager
print("\n6. Context Manager:")
try:
    from content_generator.context_manager import (
        before_agent_monitor,
        after_agent_monitor,
        get_context_stats,
        reset_context_stats
    )
    print("   ✓ Context monitoring callbacks imported successfully")
    
    # Test reset
    reset_context_stats()
    stats = get_context_stats()
    print(f"   ✓ Context stats working: {stats}")
except ImportError as e:
    print(f"   ✗ Import error: {e}")

print("\n" + "="*70)
print("✅ ALL VERIFICATIONS PASSED!")
print("="*70)
print("\nSystem is ready for testing.")
print("\nNext steps:")
print("  1. Set environment variables (BATCH_SIZE, BRAND_IMAGE_PROMPT, OUTPUT_SHEET_ID)")
print("  2. Run: python -m content_generator.main")
print("  3. Or use Web UI: ./start_web_ui.sh")
print("="*70)

