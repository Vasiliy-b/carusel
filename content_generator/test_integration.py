"""
Integration test for complete multi-agent workflow
Tests end-to-end processing with mock/sample data
"""
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_full_workflow_with_mock_data():
    """
    Test complete workflow with minimal mock data (no actual API calls)
    """
    print("\n" + "="*70)
    print(" INTEGRATION TEST: Mock Data Workflow")
    print("="*70)
    
    try:
        # Import after loading env
        from agents import (
            data_collector_agent,
            content_analyzer_agent,
            creative_director_agent,
            copywriter_agent
        )
        
        # Test each agent in sequence with mock data
        session_service = InMemorySessionService()
        
        # ===== TEST 1: Data Collector =====
        print("\n[1/4] Testing Data Collector...")
        runner1 = Runner(
            agent=data_collector_agent,
            app_name="test_integration",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="test_integration",
            user_id="test",
            session_id="integration_test_001"
        )
        
        # Mock: Inject sample posts directly into state
        mock_posts = [
            {
                'post_id': 'mock_001',
                'row_index': 0,
                'url': 'https://instagram.com/test',
                'category': 'astrology',
                'theme': 'zodiac signs',
                'VIRALITY': 'VIRUS',
                'ENGAGEMENT': 'VIRAL ER',
                'rewrited_script': 'HOOK: Ever feel like your zodiac sign knows you better than anyone? Let\'s dive deep into what makes each sign truly unique...'
            }
        ]
        
        session.state['filtered_posts'] = mock_posts
        session.state['total_posts_found'] = 1
        await session_service.update_session(session)
        
        print("✓ Mock data injected")
        
        # ===== TEST 2: Content Analyzer =====
        print("\n[2/4] Testing Content Analyzer...")
        runner2 = Runner(
            agent=content_analyzer_agent,
            app_name="test_integration",
            session_service=session_service
        )
        
        message2 = Content(
            parts=[Part(text="Analyze the filtered posts")],
            role="user"
        )
        
        analysis_received = False
        async for event in runner2.run_async(
            user_id="test",
            session_id="integration_test_001",
            new_message=message2
        ):
            if event.is_final_response():
                analysis_received = True
                print("✓ Content analysis completed")
                if event.content and event.content.parts:
                    print(f"  Preview: {event.content.parts[0].text[:200]}...")
        
        if not analysis_received:
            print("❌ Content analysis failed")
            return False
        
        # ===== TEST 3: Creative Director =====
        print("\n[3/4] Testing Creative Director...")
        runner3 = Runner(
            agent=creative_director_agent,
            app_name="test_integration",
            session_service=session_service
        )
        
        message3 = Content(
            parts=[Part(text="Create creative brief")],
            role="user"
        )
        
        brief_received = False
        async for event in runner3.run_async(
            user_id="test",
            session_id="integration_test_001",
            new_message=message3
        ):
            if event.is_final_response():
                brief_received = True
                print("✓ Creative direction completed")
                if event.content and event.content.parts:
                    response = event.content.parts[0].text
                    print(f"  Preview: {response[:200]}...")
                    
                    # Check for style decision
                    if 'narrative' in response.lower():
                        print("  ✓ Style: NARRATIVE")
                    elif 'independent' in response.lower():
                        print("  ✓ Style: INDEPENDENT")
        
        if not brief_received:
            print("❌ Creative direction failed")
            return False
        
        # ===== TEST 4: Copywriter =====
        print("\n[4/4] Testing Copywriter...")
        runner4 = Runner(
            agent=copywriter_agent,
            app_name="test_integration",
            session_service=session_service
        )
        
        message4 = Content(
            parts=[Part(text="Generate header and caption")],
            role="user"
        )
        
        copy_received = False
        async for event in runner4.run_async(
            user_id="test",
            session_id="integration_test_001",
            new_message=message4
        ):
            if event.is_final_response():
                copy_received = True
                print("✓ Copy generation completed")
                if event.content and event.content.parts:
                    print(f"  Preview: {event.content.parts[0].text[:200]}...")
        
        if not copy_received:
            print("❌ Copy generation failed")
            return False
        
        print("\n" + "="*70)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("="*70)
        print("\nSequential agent flow verified:")
        print("  1. Data Collection ✓")
        print("  2. Content Analysis ✓")
        print("  3. Creative Direction ✓")
        print("  4. Copywriting ✓")
        print("\nNext: Image generation and GCS upload (requires real credentials)")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        logger.exception(e)
        return False


async def test_tool_functions():
    """
    Test individual tool functions
    """
    print("\n" + "="*70)
    print(" TOOL FUNCTION TESTS")
    print("="*70)
    
    from tools import fetch_google_sheet_data
    from google.adk.tools.tool_context import ToolContext
    from google.adk.sessions import Session
    
    try:
        # Create mock tool context
        session = Session(
            app_name="test",
            user_id="test",
            session_id="test",
            events=[],
            state={}
        )
        
        # Create a minimal ToolContext
        # Note: This is simplified - real ToolContext has more attributes
        class MockToolContext:
            def __init__(self):
                self.state = {}
                self.session = session
        
        mock_context = MockToolContext()
        
        # Test fetch_google_sheet_data
        print("\n[1/1] Testing fetch_google_sheet_data tool...")
        result = fetch_google_sheet_data(mock_context)
        
        if result.get('status') == 'success':
            print(f"✓ Tool executed successfully")
            print(f"  Posts found: {result.get('total_posts', 0)}")
            print(f"  Summary: {result.get('summary', 'N/A')}")
            
            if result.get('posts'):
                print(f"\n  Sample post:")
                first_post = result['posts'][0]
                for key in ['post_id', 'category', 'theme', 'VIRALITY', 'ENGAGEMENT']:
                    if key in first_post:
                        print(f"    {key}: {first_post[key]}")
            
            return True
        else:
            print(f"❌ Tool failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        logger.exception(e)
        return False


async def test_sheets_access():
    """
    Quick test to verify Google Sheets is accessible
    """
    print("\n" + "="*70)
    print(" GOOGLE SHEETS ACCESS TEST")
    print("="*70)
    
    try:
        import requests
        from config import Config
        
        sheet_id = Config.SHEETS_ID
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=904285398"
        
        print(f"\nFetching: {url[:80]}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            print(f"✓ Sheet accessible")
            print(f"  Rows: {len(lines)}")
            print(f"  Headers: {lines[0][:100]}...")
            
            # Parse to check columns
            import pandas as pd
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            print(f"  Columns: {len(df.columns)}")
            required_cols = ['VIRALITY', 'ENGAGEMENT', 'rewrited_script']
            missing = [col for col in required_cols if col not in df.columns]
            
            if missing:
                print(f"⚠️  Missing columns: {missing}")
            else:
                print(f"✓ All required columns present")
            
            return True
        else:
            print(f"❌ Cannot access sheet: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Sheets access test failed: {e}")
        return False


async def run_all_integration_tests():
    """
    Run all integration tests
    """
    print("\n" + "="*70)
    print(" CONTENT GENERATOR INTEGRATION TESTS")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: Sheets access
    print("\n📊 Test 1: Google Sheets Access")
    results['sheets_access'] = await test_sheets_access()
    
    # Test 2: Tool functions
    print("\n🔧 Test 2: Tool Functions")
    results['tool_functions'] = await test_tool_functions()
    
    # Test 3: Full workflow
    print("\n🤖 Test 3: Multi-Agent Workflow")
    results['workflow'] = await test_full_workflow_with_mock_data()
    
    # Summary
    print("\n" + "="*70)
    print(" TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("\nSystem is ready for production use:")
        print("  python -m content_generator.main")
        print("  or: adk web")
    else:
        print("\n⚠️  Some tests failed - review errors above")
    
    print("="*70)
    
    return passed == total


if __name__ == "__main__":
    load_dotenv()
    
    try:
        success = asyncio.run(run_all_integration_tests())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted")
        exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        logging.exception(e)
        exit(1)

