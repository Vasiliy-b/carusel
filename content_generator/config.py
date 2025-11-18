"""
Configuration management for Content Generator
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the correct location
# Look for .env in the content_generator directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Central configuration class"""
    
    # ============================================
    # Google Cloud Configuration
    # ============================================
    PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
    LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
    USE_VERTEX_AI = os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE').upper() == 'TRUE'
    
    # Cloud Storage
    GCS_BUCKET = os.getenv('GCS_BUCKET', 'content-generator-output')
    GCS_BUCKET_PUBLIC = os.getenv('GCS_BUCKET_PUBLIC', 'TRUE').upper() == 'TRUE'
    
    # ============================================
    # Authentication
    # ============================================
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    SHEETS_SERVICE_ACCOUNT_PATH = os.getenv('SHEETS_SERVICE_ACCOUNT_PATH')
    
    # ============================================
    # Google Sheets
    # ============================================
    SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID', '10sNSObpUUfxtPs04owXeZjMm-dr-Z3Xh-UYXnepG5MM')
    SOURCE_SHEET_NAME = os.getenv('SOURCE_SHEET_NAME', 'INSTAGRAM')
    OUTPUT_MODE = os.getenv('OUTPUT_MODE', 'new_tab')
    OUTPUT_SHEET_NAME = os.getenv('OUTPUT_SHEET_NAME', 'Generated_Content')
    OUTPUT_COLUMN_PREFIX = os.getenv('OUTPUT_COLUMN_PREFIX', 'gen_')
    
    # ============================================
    # Filtering Criteria
    # ============================================
    VIRALITY_FILTER = [v.strip() for v in os.getenv('VIRALITY_FILTER', 'VIRUS,BEST,GOOD').split(',')]
    ENGAGEMENT_FILTER = [e.strip() for e in os.getenv('ENGAGEMENT_FILTER', 'BEST ER,VIRAL ER').split(',')]
    
    # ============================================
    # Model Configuration
    # ============================================
    TEXT_MODEL = os.getenv('TEXT_MODEL', 'gemini-2.5-flash')
    IMAGE_MODEL = os.getenv('IMAGE_MODEL', 'gemini-2.5-flash-image')  # nanobabana
    
    # ============================================
    # Generation Settings
    # ============================================
    CAROUSEL_IMAGE_COUNT = int(os.getenv('CAROUSEL_IMAGE_COUNT', '10'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '0'))  # 0 = unlimited
    ENABLE_TEXT_OVERLAY_FALLBACK = os.getenv('ENABLE_TEXT_OVERLAY_FALLBACK', 'TRUE').upper() == 'TRUE'
    IMAGE_FORMAT = os.getenv('IMAGE_FORMAT', 'PNG').upper()
    IMAGE_QUALITY = int(os.getenv('IMAGE_QUALITY', '95'))
    IMAGE_ASPECT_RATIO = os.getenv('IMAGE_ASPECT_RATIO', '1:1')  # 1:1, 4:5, 9:16, 16:9, etc.
    
    # Image Style Suffix (auto-appended to every image prompt for consistent styling)
    # Default empty - only use when NOT using style reference images
    STYLE = os.getenv('STYLE', '')
    
    # ============================================
    # Processing Options
    # ============================================
    PARALLEL_IMAGE_GENERATION = os.getenv('PARALLEL_IMAGE_GENERATION', 'TRUE').upper() == 'TRUE'
    MAX_PARALLEL_IMAGES = int(os.getenv('MAX_PARALLEL_IMAGES', '10'))
    MAX_CONCURRENT_IMAGE_REQUESTS = int(os.getenv('MAX_CONCURRENT_IMAGE_REQUESTS', '3'))
    RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '2'))
    
    # ============================================
    # Logging & Monitoring
    # ============================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/content_generator.log')
    ENABLE_EVENT_LOGGING = os.getenv('ENABLE_EVENT_LOGGING', 'TRUE').upper() == 'TRUE'
    TRACK_COSTS = os.getenv('TRACK_COSTS', 'FALSE').upper() == 'TRUE'
    
    # ============================================
    # Advanced Settings
    # ============================================
    SESSION_ID_PREFIX = os.getenv('SESSION_ID_PREFIX', 'content_gen')
    ENABLE_STATE_PERSISTENCE = os.getenv('ENABLE_STATE_PERSISTENCE', 'FALSE').upper() == 'TRUE'
    STATE_STORAGE_PATH = os.getenv('STATE_STORAGE_PATH', './state')
    IMAGE_GENERATION_TIMEOUT = int(os.getenv('IMAGE_GENERATION_TIMEOUT', '60'))
    TEXT_GENERATION_TIMEOUT = int(os.getenv('TEXT_GENERATION_TIMEOUT', '30'))
    
    # ============================================
    # Image Upload Settings
    # ============================================
    MAX_REFERENCE_IMAGES = 2
    ALLOWED_IMAGE_FORMATS = ['PNG', 'JPEG', 'JPG', 'WEBP']
    MAX_UPLOAD_SIZE_MB = 10
    REFERENCE_IMAGE_STORAGE = os.getenv('REFERENCE_IMAGE_STORAGE', './temp/reference_images')
    
    # ============================================
    # Input Mode
    # ============================================
    DEFAULT_INPUT_MODE = os.getenv('DEFAULT_INPUT_MODE', 'sheet')  # 'sheet' or 'text'
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.SHEETS_ID:
            errors.append("GOOGLE_SHEETS_ID is required")
        
        if cls.USE_VERTEX_AI and not cls.PROJECT_ID:
            errors.append("GOOGLE_CLOUD_PROJECT required when using Vertex AI")
        
        if not cls.USE_VERTEX_AI and not cls.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY required when not using Vertex AI")
        
        if not cls.GCS_BUCKET:
            errors.append("GCS_BUCKET is required")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True


# Validate on import
Config.validate()

