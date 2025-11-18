"""
Main application entry point for Multi-Agent Content Generator
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from .config import Config

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create handlers
handlers = [logging.StreamHandler(sys.stdout)]

if Config.LOG_FILE:
    # Ensure log file path is absolute
    log_file_path = Path(Config.LOG_FILE)
    if not log_file_path.is_absolute():
        log_file_path = Path(__file__).parent.parent / Config.LOG_FILE
    
    # Create parent directory if needed
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add file handler with explicit encoding and no buffering
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handlers.append(file_handler)

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers,
    force=True  # Override any existing config
)

logger = logging.getLogger(__name__)


async def run_content_generator():
    """
    Main execution function for content generation workflow
    """
    try:
        # Check input mode from environment
        input_mode = os.getenv('INPUT_MODE', 'sheet')
        user_text = os.getenv('USER_TEXT_INPUT', '')
        
        logger.info("="*70)
        logger.info("MULTI-AGENT CONTENT GENERATOR STARTED")
        logger.info("="*70)
        logger.info(f"Configuration:")
        logger.info(f"  - Input Mode: {input_mode.upper()}")
        logger.info(f"  - Text Model: {Config.TEXT_MODEL}")
        logger.info(f"  - Image Model: {Config.IMAGE_MODEL}")
        logger.info(f"  - GCS Bucket: {Config.GCS_BUCKET}")
        if input_mode == 'sheet':
            logger.info(f"  - Source Sheet: {Config.SHEETS_ID}/{Config.SOURCE_SHEET_NAME}")
            logger.info(f"  - Filters: VIRALITY={Config.VIRALITY_FILTER}, ENGAGEMENT={Config.ENGAGEMENT_FILTER}")
        else:
            logger.info(f"  - Text Input: {len(user_text)} characters")
        logger.info("="*70)
        
        # Load reference images if provided
        reference_images = {}
        if os.getenv('REFERENCE_STYLE_IMAGE'):
            try:
                with open(os.getenv('REFERENCE_STYLE_IMAGE'), 'rb') as f:
                    reference_images['style'] = f.read()
                logger.info(f"  - Style reference image loaded")
            except Exception as e:
                logger.warning(f"Could not load style reference image: {e}")
        
        if os.getenv('REFERENCE_PERSONA_IMAGE'):
            try:
                with open(os.getenv('REFERENCE_PERSONA_IMAGE'), 'rb') as f:
                    reference_images['persona'] = f.read()
                logger.info(f"  - Persona reference image loaded")
            except Exception as e:
                logger.warning(f"Could not load persona reference image: {e}")
        
        # Initialize session service
        session_service = InMemorySessionService()
        logger.info("Session service initialized")
        
        # Get appropriate root agent for mode
        from .orchestrator import create_root_agent_for_mode
        root_agent = create_root_agent_for_mode(input_mode)
        logger.info(f"Root agent created for {input_mode} mode")
        
        # Create runner with root agent
        runner = Runner(
            agent=root_agent,
            app_name="content_generator",
            session_service=session_service
        )
        logger.info("Runner initialized with root coordinator agent")
        
        # Create unique session ID
        session_id = f"{Config.SESSION_ID_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        user_id = "system"
        
        # Create session
        session = await session_service.create_session(
            app_name="content_generator",
            user_id=user_id,
            session_id=session_id
        )
        logger.info(f"Session created: {session_id}")
        
        # Create initial message based on mode
        if input_mode == 'text':
            message_text = f"Process this content idea: {user_text}"
            logger.info(f"Text mode: Input passed via environment variable USER_TEXT_INPUT")
            if reference_images:
                logger.info(f"Text mode: {len(reference_images)} reference image(s) will be loaded from env vars")
        else:
            message_text = "Process all qualifying Instagram posts and generate carousel content"
            logger.info("Sheet mode: Will fetch posts from Google Sheets")
        
        # Initial message to trigger workflow
        user_message = Content(
            parts=[Part(text=message_text)],
            role="user"
        )
        
        logger.info("Starting agent workflow...")
        logger.info("-"*70)
        
        # Track events
        event_count = 0
        final_response = None
        
        # Run agent asynchronously
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            event_count += 1
            
            # Log event details if enabled
            if Config.ENABLE_EVENT_LOGGING:
                logger.debug(f"Event {event_count}: Author={event.author}")
                if event.content and event.content.parts:
                    content_preview = str(event.content.parts[0])[:200]
                    logger.debug(f"  Content: {content_preview}...")
            
            # Log agent transitions
            if event.author and event.content:
                if event.content.parts and len(event.content.parts) > 0:
                    part = event.content.parts[0]
                    if hasattr(part, 'text') and part.text:
                        # Log agent outputs
                        logger.info(f"[{event.author}] {part.text[:150]}...")
            
            # Capture final response
            if event.is_final_response():
                final_response = event
                logger.info("="*70)
                logger.info("FINAL RESPONSE RECEIVED")
                logger.info("="*70)
                if event.content and event.content.parts:
                    print("\n" + "="*70)
                    print("GENERATION COMPLETE!")
                    print("="*70)
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            print(part.text)
                    print("="*70)
        
        # Summary
        logger.info(f"\nWorkflow completed successfully!")
        logger.info(f"Total events processed: {event_count}")
        logger.info(f"Session ID: {session_id}")
        
        # Get final state
        final_session = await session_service.get_session(
            app_name="content_generator",
            user_id=user_id,
            session_id=session_id
        )
        
        # Extract results from state
        if final_session and final_session.state:
            total_posts = final_session.state.get('total_posts_found', 0)
            logger.info(f"Posts processed: {total_posts}")
            
            # Check for any stored metadata
            metadata_keys = [k for k in final_session.state.keys() if k.startswith('metadata_')]
            if metadata_keys:
                logger.info(f"Generated content metadata stored: {len(metadata_keys)} posts")
        
        return {
            "status": "success",
            "session_id": session_id,
            "events_processed": event_count,
            "final_response": final_response
        }
        
    except KeyboardInterrupt:
        logger.warning("\n\nWorkflow interrupted by user")
        return {"status": "interrupted"}
        
    except Exception as e:
        logger.error(f"Error in content generator: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def main():
    """
    CLI entry point
    """
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Run async workflow
        result = asyncio.run(run_content_generator())
        
        if result['status'] == 'success':
            logger.info("\n✅ Content generation completed successfully!")
            sys.exit(0)
        elif result['status'] == 'interrupted':
            logger.info("\n⚠️  Workflow interrupted")
            sys.exit(1)
        else:
            logger.error(f"\n❌ Content generation failed: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

