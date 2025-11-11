"""
Simple test script to verify basic functionality
"""
import asyncio
import logging
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_data_collector():
    """Test the data collector agent"""
    print("\n" + "="*70)
    print("TEST 1: Data Collector Agent")
    print("="*70)
    
    try:
        from agents import data_collector_agent
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=data_collector_agent,
            app_name="test_data_collector",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="test_data_collector",
            user_id="test",
            session_id="test_001"
        )
        
        message = Content(
            parts=[Part(text="Fetch and filter Instagram posts")],
            role="user"
        )
        
        print("\nFetching posts from Google Sheets...")
        
        async for event in runner.run_async(
            user_id="test",
            session_id="test_001",
            new_message=message
        ):
            if event.is_final_response() and event.content:
                print("\n✓ Data Collector Test Passed!")
                if event.content.parts:
                    print(f"Response: {event.content.parts[0].text[:500]}...")
                
                # Check state
                final_session = await session_service.get_session(
                    app_name="test_data_collector",
                    user_id="test",
                    session_id="test_001"
                )
                
                if 'total_posts_found' in final_session.state:
                    print(f"\nPosts found: {final_session.state['total_posts_found']}")
                
                return True
        
        print("❌ No final response received")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception(e)
        return False


async def test_content_analyzer():
    """Test content analyzer with sample data"""
    print("\n" + "="*70)
    print("TEST 2: Content Analyzer Agent")
    print("="*70)
    
    try:
        from agents import content_analyzer_agent
        
        # Create sample post data
        sample_posts = [
            {
                'post_id': 'test_001',
                'rewrited_script': 'HOOK: Ever wondered why Aries are so confident? Here\'s the secret...',
                'category': 'astrology',
                'theme': 'zodiac personalities',
                'VIRALITY': 'BEST',
                'ENGAGEMENT': 'VIRAL ER'
            }
        ]
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=content_analyzer_agent,
            app_name="test_analyzer",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="test_analyzer",
            user_id="test",
            session_id="test_002"
        )
        
        # Set filtered_posts in state
        session.state['filtered_posts'] = sample_posts
        await session_service.update_session(session)
        
        message = Content(
            parts=[Part(text="Analyze the filtered posts")],
            role="user"
        )
        
        print("\nAnalyzing sample post...")
        
        async for event in runner.run_async(
            user_id="test",
            session_id="test_002",
            new_message=message
        ):
            if event.is_final_response() and event.content:
                print("\n✓ Content Analyzer Test Passed!")
                if event.content.parts:
                    print(f"Analysis: {event.content.parts[0].text[:500]}...")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception(e)
        return False


async def test_creative_director():
    """Test creative director with sample analysis"""
    print("\n" + "="*70)
    print("TEST 3: Creative Director Agent")
    print("="*70)
    
    try:
        from agents import creative_director_agent
        
        # Sample analysis
        sample_analysis = """
        Post Analysis:
        - Topic: Zodiac sign personality traits (Aries)
        - Content Type: Educational/entertainment
        - Tone: Inspirational and relatable
        - Audience: Astrology enthusiasts, young adults
        - Narrative: List-based, multiple personality traits
        """
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=creative_director_agent,
            app_name="test_director",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="test_director",
            user_id="test",
            session_id="test_003"
        )
        
        session.state['content_analysis'] = sample_analysis
        await session_service.update_session(session)
        
        message = Content(
            parts=[Part(text="Create creative brief based on analysis")],
            role="user"
        )
        
        print("\nCreating creative brief...")
        
        async for event in runner.run_async(
            user_id="test",
            session_id="test_003",
            new_message=message
        ):
            if event.is_final_response() and event.content:
                print("\n✓ Creative Director Test Passed!")
                if event.content.parts:
                    response = event.content.parts[0].text
                    print(f"Creative Brief: {response[:500]}...")
                    
                    # Check if it decided on style
                    if 'narrative' in response.lower() or 'independent' in response.lower():
                        print("✓ Style decision made")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception(e)
        return False


async def run_all_tests():
    """Run all test functions"""
    print("\n" + "="*70)
    print(" RUNNING CONTENT GENERATOR TESTS")
    print("="*70)
    
    results = {}
    
    # Test 1: Data Collector
    results['data_collector'] = await test_data_collector()
    
    # Test 2: Content Analyzer  
    results['content_analyzer'] = await test_content_analyzer()
    
    # Test 3: Creative Director
    results['creative_director'] = await test_creative_director()
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*70)
    
    return all(results.values())


if __name__ == "__main__":
    load_dotenv()
    
    try:
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted")
        exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        exit(1)

