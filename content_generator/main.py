"""
Main application entry point for Multi-Agent Content Generator
"""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from .config import Config
from .orchestrator import root_agent

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE) if Config.LOG_FILE else logging.StreamHandler(),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def run_content_generator():
    """
    Main execution function for content generation workflow
    """
    try:
        logger.info("="*70)
        logger.info("MULTI-AGENT CONTENT GENERATOR STARTED")
        logger.info("="*70)
        logger.info(f"Configuration:")
        logger.info(f"  - Text Model: {Config.TEXT_MODEL}")
        logger.info(f"  - Image Model: {Config.IMAGE_MODEL}")
        logger.info(f"  - GCS Bucket: {Config.GCS_BUCKET}")
        logger.info(f"  - Source Sheet: {Config.SHEETS_ID}/{Config.SOURCE_SHEET_NAME}")
        logger.info(f"  - Filters: VIRALITY={Config.VIRALITY_FILTER}, ENGAGEMENT={Config.ENGAGEMENT_FILTER}")
        logger.info("="*70)
        
        # Initialize session service
        session_service = InMemorySessionService()
        logger.info("Session service initialized")
        
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
        
        # Initial message to trigger workflow
        user_message = Content(
            parts=[Part(text="Process all qualifying Instagram posts and generate carousel content")],
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

