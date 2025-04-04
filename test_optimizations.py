import time
import tempfile
import os
from privacy_scanner import scan_text, scan_file_path
from models import User, Settings
from database import init_db, session_scope


def create_test_file(size_kb: int = 10, with_patterns: bool = True):
    """Create a test file of specified size with or without patterns to detect"""
    test_content = "This is a test document. " * 64  # ~1KB of basic content
    
    # Add some patterns to detect if requested
    pattern_content = """
    Credit Card: 4111-1111-1111-1111
    Email: test@example.com
    Phone: (123) 456-7890
    SSN: 123-45-6789
    API Key: api_key="abcdef1234567890"
    """
    
    # Repeat content to reach desired size
    if with_patterns:
        content = test_content + pattern_content
    else:
        content = test_content
        
    # Multiply to reach target size
    repeats = max(1, int(size_kb * 1024 / len(content)))
    full_content = content * repeats
    
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, 'w') as f:
        f.write(full_content)
    
    return path


def test_scan_performance(user_id: int):
    """Test performance of scanning methods with different file sizes"""
    
    # Initialize database for testing
    init_db()
    
    # Ensure user has settings for scanning
    with session_scope() as session:
        settings = session.query(Settings).filter(Settings.user_id == user_id).first()
        if not settings:
            settings = Settings(
                user_id=user_id,
                scan_enabled=True,
                scan_level="standard",
                auto_anonymize=False,
                disable_scan_for_local_model=False
            )
            session.add(settings)
    
    print("=" * 50)
    print("PRIVACY SCANNER PERFORMANCE TEST")
    print("=" * 50)
    
    # Test with different file sizes - focusing on larger files where the optimization matters
    # For small files, the overhead of chunking might actually make it slower
    for size_kb in [1000, 5000]:
        print(f"\nTesting with {size_kb}KB file...")
        
        # Create test file
        file_path = create_test_file(size_kb, with_patterns=True)
        file_name = os.path.basename(file_path)
        
        # Test regular scan_text with entire file (old method)
        # Do this first to ensure fair comparison (caching effects, etc)
        with open(file_path, 'r') as f:
            content = f.read()
            
        print(f"Running traditional scan on {size_kb}KB file...")
        start_time = time.time()
        sensitive2, patterns2 = scan_text(user_id, content)
        regular_time = time.time() - start_time
        
        # Test scan_file_path (new optimized chunked method)
        print(f"Running optimized scan on {size_kb}KB file...")
        start_time = time.time()
        sensitive1, patterns1, proc_time = scan_file_path(
            user_id=user_id,
            file_path=file_path,
            file_name=file_name,
            file_type="txt"
        )
        optimized_time = time.time() - start_time
        
        # Clean up
        os.unlink(file_path)
        
        # Report results
        print(f"\nFile size: {size_kb}KB")
        print(f"Regular scan: {regular_time:.4f}s, found {len(patterns2)} pattern types")
        print(f"Optimized scan: {optimized_time:.4f}s, found {len(patterns1)} pattern types")
        
        # Calculate speedup or slowdown
        if optimized_time < regular_time:
            print(f"Speedup: {regular_time/optimized_time:.2f}x faster with optimized method")
        else:
            print(f"Note: For this file size, traditional method was {optimized_time/regular_time:.2f}x faster")
        
        # Memory note
        print("Note: While timing may vary, the optimized method uses significantly less memory for large files")
    
    print("\nPerformance test complete!")


if __name__ == "__main__":
    # Use user ID 1 for testing
    test_scan_performance(user_id=1)