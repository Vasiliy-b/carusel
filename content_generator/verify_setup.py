"""
Setup verification script
Run this before starting the main application to verify all credentials and configurations
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def verify_setup():
    """
    Verify all required configurations and credentials
    """
    print("🔍 Verifying Content Generator Setup...\n")
    print("="*70)
    
    issues = []
    warnings = []
    success_checks = []
    
    # ============================================
    # Check Environment Variables
    # ============================================
    print("\n📋 Checking Environment Variables...")
    
    required_vars = {
        'GOOGLE_CLOUD_PROJECT': 'GCP Project ID',
        'GOOGLE_CLOUD_LOCATION': 'GCP Location',
        'GCS_BUCKET': 'Cloud Storage Bucket',
        'GOOGLE_SHEETS_ID': 'Google Sheets ID'
    }
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            issues.append(f"❌ Missing: {var} ({description})")
        else:
            success_checks.append(f"✓ {description}: {value}")
    
    # ============================================
    # Check Authentication
    # ============================================
    print("\n🔐 Checking Authentication...")
    
    use_vertex = os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE').upper() == 'TRUE'
    
    if use_vertex:
        success_checks.append("✓ Using Vertex AI authentication")
        
        # Check for service account or ADC
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if os.path.exists(cred_path):
                success_checks.append(f"✓ Service account key found: {cred_path}")
            else:
                issues.append(f"❌ Service account key not found: {cred_path}")
        else:
            warnings.append("⚠️  No GOOGLE_APPLICATION_CREDENTIALS - assuming ADC configured (run: gcloud auth application-default login)")
    else:
        success_checks.append("✓ Using Google AI Studio")
        if not os.getenv('GOOGLE_API_KEY'):
            issues.append("❌ GOOGLE_API_KEY required when not using Vertex AI")
        else:
            success_checks.append("✓ Google API Key configured")
    
    # ============================================
    # Check Google Cloud Storage
    # ============================================
    print("\n☁️  Checking Google Cloud Storage...")
    
    try:
        from google.cloud import storage
        
        bucket_name = os.getenv('GCS_BUCKET')
        if bucket_name:
            try:
                client = storage.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))
                bucket = client.bucket(bucket_name)
                
                if bucket.exists():
                    success_checks.append(f"✓ GCS bucket exists: {bucket_name}")
                else:
                    warnings.append(f"⚠️  GCS bucket does not exist: {bucket_name} (will be created on first run)")
            except Exception as e:
                issues.append(f"❌ Cannot access GCS: {str(e)}")
    except ImportError:
        issues.append("❌ google-cloud-storage not installed (run: pip install -r requirements.txt)")
    
    # ============================================
    # Check Google Sheets Access
    # ============================================
    print("\n📊 Checking Google Sheets Access...")
    
    try:
        import requests
        
        sheet_id = os.getenv('GOOGLE_SHEETS_ID')
        if sheet_id:
            # Test public access
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=904285398"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                success_checks.append(f"✓ Google Sheets accessible (public): {sheet_id}")
                
                # Check if it has data
                lines = response.text.split('\n')
                success_checks.append(f"✓ Sheet contains {len(lines)} rows")
            else:
                issues.append(f"❌ Cannot access Google Sheets: HTTP {response.status_code}")
    except ImportError:
        issues.append("❌ requests library not installed")
    except Exception as e:
        issues.append(f"❌ Sheets access error: {str(e)}")
    
    # ============================================
    # Check Required Python Packages
    # ============================================
    print("\n📦 Checking Python Dependencies...")
    
    required_packages = [
        ('google.adk', 'google-adk'),
        ('google.cloud.storage', 'google-cloud-storage'),
        ('pandas', 'pandas'),
        ('PIL', 'Pillow'),
        ('dotenv', 'python-dotenv'),
        ('requests', 'requests')
    ]
    
    optional_packages = [
        ('gspread', 'gspread (for sheet updates)')
    ]
    
    for module, package in required_packages:
        try:
            __import__(module)
            success_checks.append(f"✓ {package} installed")
        except ImportError:
            issues.append(f"❌ Missing package: {package}")
    
    for module, package in optional_packages:
        try:
            __import__(module)
            success_checks.append(f"✓ {package} installed")
        except ImportError:
            warnings.append(f"⚠️  Optional: {package} not installed (sheet updates will be limited)")
    
    # ============================================
    # Check Model Configuration
    # ============================================
    print("\n🤖 Checking Model Configuration...")
    
    text_model = os.getenv('TEXT_MODEL', 'gemini-2.5-flash')
    image_model = os.getenv('IMAGE_MODEL', 'gemini-2.5-flash-image')
    
    success_checks.append(f"✓ Text model: {text_model}")
    success_checks.append(f"✓ Image model: {image_model}")
    
    if image_model != 'gemini-2.5-flash-image':
        warnings.append(f"⚠️  Image model is '{image_model}' - expected 'gemini-2.5-flash-image' (nanobabana)")
    
    # ============================================
    # Check Directories
    # ============================================
    print("\n📁 Checking Directories...")
    
    # Create necessary directories
    dirs_to_create = ['logs', 'output', 'state']
    for dir_name in dirs_to_create:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            success_checks.append(f"✓ Created directory: {dir_name}/")
        else:
            success_checks.append(f"✓ Directory exists: {dir_name}/")
    
    # ============================================
    # Print Results
    # ============================================
    print("\n" + "="*70)
    print("VERIFICATION RESULTS")
    print("="*70)
    
    if success_checks:
        print("\n✅ Passed Checks:")
        for check in success_checks:
            print(f"  {check}")
    
    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  {warning}")
    
    if issues:
        print("\n❌ CRITICAL ISSUES - Must Fix Before Running:")
        for issue in issues:
            print(f"  {issue}")
        print("\n" + "="*70)
        print("Setup incomplete. Please fix the issues above.")
        print("="*70)
        return False
    else:
        print("\n" + "="*70)
        print("✅ ALL CHECKS PASSED - System ready to run!")
        print("="*70)
        print("\nTo start the content generator:")
        print("  python -m content_generator.main")
        print("\nOr use ADK web UI:")
        print("  adk web")
        print("="*70)
        return True


async def test_agent_connection():
    """
    Quick test to verify agent can connect to models
    """
    print("\n🧪 Testing Agent Connection...")
    
    try:
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai.types import Content, Part
        
        # Create a simple test agent
        test_agent = LlmAgent(
            name="TestAgent",
            model=os.getenv('TEXT_MODEL', 'gemini-2.5-flash'),
            instruction="Respond with: Connection successful!"
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=test_agent,
            app_name="agent_connection_test",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="agent_connection_test",
            user_id="test",
            session_id="test_001"
        )
        
        test_message = Content(
            parts=[Part(text="Test connection")],
            role="user"
        )
        
        async for event in runner.run_async(
            user_id="test",
            session_id="test_001",
            new_message=test_message
        ):
            if event.is_final_response() and event.content:
                print(f"✓ Agent connection test successful!")
                response_text = event.content.parts[0].text if event.content.parts else 'No text'
                print(f"  Model response: {response_text[:100]}...")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Agent connection test failed: {e}")
        return False


def main():
    """
    Main verification script entry point
    """
    print("\n" + "="*70)
    print(" CONTENT GENERATOR SETUP VERIFICATION")
    print("="*70 + "\n")
    
    # Run basic verification
    basic_ok = verify_setup()
    
    if not basic_ok:
        sys.exit(1)
    
    # Ask if user wants to test connection
    print("\nWould you like to test agent connection? (y/n): ", end='')
    try:
        response = input().strip().lower()
        if response == 'y':
            test_ok = asyncio.run(test_agent_connection())
            if not test_ok:
                print("\n⚠️  Agent test failed - check your credentials")
                sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nSkipping connection test")
    
    print("\n✅ Verification complete - system is ready!")
    sys.exit(0)


if __name__ == "__main__":
    main()

