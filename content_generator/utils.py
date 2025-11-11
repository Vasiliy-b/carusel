"""
Utility functions for content generator
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def save_to_json(data: Any, filepath: str):
    """Save data to JSON file"""
    try:
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved data to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
        return False


def load_from_json(filepath: str) -> Optional[Any]:
    """Load data from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded data from {filepath}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON: {e}")
        return None


def format_post_summary(post: Dict[str, Any]) -> str:
    """
    Format a post dictionary into a readable summary
    """
    summary = f"""
Post ID: {post.get('post_id', 'N/A')}
Category: {post.get('category', 'N/A')}
Theme: {post.get('theme', 'N/A')}
Virality: {post.get('VIRALITY', 'N/A')}
Engagement: {post.get('ENGAGEMENT', 'N/A')}
URL: {post.get('url', 'N/A')}
"""
    return summary.strip()


def parse_rewrited_script(script: str) -> Dict[str, str]:
    """
    Parse rewrited_script column to extract structured elements
    Looks for common patterns like HOOK:, BODY:, etc.
    """
    result = {
        'full_text': script,
        'hook': '',
        'body': '',
        'cta': ''
    }
    
    if not script:
        return result
    
    # Try to extract HOOK if labeled
    if 'HOOK:' in script.upper():
        parts = script.split('HOOK:', 1)
        if len(parts) > 1:
            hook_part = parts[1].split('\n')[0].strip()
            result['hook'] = hook_part
    
    # Otherwise, just use the full text
    if not result['hook']:
        result['hook'] = script[:200]  # First 200 chars as hook
    
    return result


def create_gcs_path(bucket: str, post_id: str, filename: str) -> str:
    """
    Create standardized GCS path
    """
    return f"gs://{bucket}/posts/{post_id}/{filename}"


def create_public_url(bucket: str, blob_name: str) -> str:
    """
    Create public HTTP URL for GCS object
    """
    return f"https://storage.googleapis.com/{bucket}/{blob_name}"


def validate_post_data(post: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that post has required fields
    
    Returns:
        (is_valid, error_message)
    """
    required_fields = ['rewrited_script', 'VIRALITY', 'ENGAGEMENT']
    
    for field in required_fields:
        if field not in post or not post[field]:
            return False, f"Missing required field: {field}"
    
    # Check if script has content
    script = post.get('rewrited_script', '')
    if len(script.strip()) < 10:
        return False, "Script too short or empty"
    
    return True, None


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Extract JSON object from text that might contain markdown or other formatting
    """
    try:
        # Try direct parse first
        return json.loads(text)
    except:
        pass
    
    try:
        # Look for JSON in code blocks
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            json_str = text[start:end].strip()
            return json.loads(json_str)
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            json_str = text[start:end].strip()
            return json.loads(json_str)
        else:
            # Try to find {...} or [...]
            import re
            json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
    except Exception as e:
        logger.warning(f"Could not extract JSON from text: {e}")
    
    return None


def generate_report(
    posts_processed: int,
    successful: int,
    failed: int,
    execution_time: float,
    errors: List[Dict[str, Any]] = None
) -> str:
    """
    Generate execution report
    """
    report = f"""
{'='*70}
CONTENT GENERATION REPORT
{'='*70}
Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Duration: {execution_time:.2f} seconds

Posts Processed: {posts_processed}
  ✓ Successful: {successful}
  ✗ Failed: {failed}
  Success Rate: {(successful/posts_processed*100) if posts_processed > 0 else 0:.1f}%

{'='*70}
"""
    
    if errors:
        report += "\nErrors Encountered:\n"
        for idx, error in enumerate(errors, 1):
            report += f"\n{idx}. {error.get('agent', 'Unknown')}: {error.get('error', 'Unknown error')}\n"
            report += f"   Time: {error.get('timestamp', 'N/A')}\n"
    
    report += f"\n{'='*70}\n"
    
    return report


class ProgressTracker:
    """
    Track progress across batch processing
    """
    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.successful = 0
        self.failed = 0
        self.start_time = datetime.now()
    
    def update(self, success: bool = True):
        """Update progress"""
        self.current += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1
    
    def get_progress(self) -> str:
        """Get progress string"""
        percent = (self.current / self.total * 100) if self.total > 0 else 0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed if elapsed > 0 else 0
        eta = (self.total - self.current) / rate if rate > 0 else 0
        
        return f"[{self.current}/{self.total}] {percent:.1f}% | {rate:.2f} posts/sec | ETA: {eta:.0f}s"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'total': self.total,
            'processed': self.current,
            'successful': self.successful,
            'failed': self.failed,
            'success_rate': (self.successful / self.current * 100) if self.current > 0 else 0,
            'elapsed_seconds': elapsed,
            'rate_per_second': self.current / elapsed if elapsed > 0 else 0
        }

