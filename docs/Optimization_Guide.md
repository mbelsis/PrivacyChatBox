# Performance Optimization Guide for PrivacyChatBoX

This document outlines the performance optimizations implemented in the PrivacyChatBoX application, focusing on improving scanning speed, memory efficiency, and overall application responsiveness.

## 1. Regex Engine Optimization

### Pre-compiled Regex Patterns

The original implementation compiled regex patterns on every match operation, which was inefficient. We've improved this by pre-compiling all regex patterns at module load time:

```python
# Before
for pattern_name, pattern in patterns.items():
    matches = re.findall(pattern, text)  # Compiles pattern every time

# After
# At module load time
COMPILED_PATTERNS = {}
for pattern in DEFAULT_PATTERNS:
    COMPILED_PATTERNS[pattern["name"]] = {
        "regex": re.compile(pattern["pattern"]),
        "level": pattern["level"],
        "confidence": pattern["confidence"]
    }

# During scanning
for pattern_name, pattern_info in compiled_patterns.items():
    matches = pattern_info["regex"].findall(text)  # Uses pre-compiled pattern
```

### Confidence Scoring System

We've added a confidence scoring system to each pattern to reduce false positives:

```python
DEFAULT_PATTERNS = [
    {"name": "credit_card", "pattern": r"...", "level": "standard", "confidence": 0.95},
    {"name": "email", "pattern": r"...", "level": "standard", "confidence": 0.9},
    # ...
]
```

The scan_text function now accepts a `minimum_confidence` parameter (default: 0.7) that filters out patterns with low confidence scores, reducing false positives while maintaining detection accuracy.

## 2. File Processing Optimization

### Chunked File Reading

Large files are now processed in chunks to prevent memory issues:

- `file_processor.py` provides specialized extractors for different file types
- Each extractor yields text in manageable chunks
- Supported file types include:
  - PDF files (using pdfminer.six)
  - Word documents (using python-docx)
  - Excel spreadsheets (using openpyxl)
  - CSV files
  - Plain text files

Example usage:

```python
from file_processor import scan_file_chunks

# Scan a large PDF file
sensitive, patterns, time_taken = scan_file_chunks(
    file_path="large_document.pdf",
    file_type="pdf",
    scanner_func=scan_function,
    chunk_size=2000,
    max_workers=4
)
```

## 3. Parallel Processing with ThreadPoolExecutor

File scanning now uses parallel processing to improve performance:

```python
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    # Submit all scan tasks
    future_to_chunk = {executor.submit(scanner_func, chunk): i for i, chunk in enumerate(chunks)}
    
    # Process results as they complete
    for future in future_to_chunk:
        chunk_sensitive, chunk_detected = future.result()
        # Merge results...
```

Benefits:
- Faster processing of large files
- Better utilization of multi-core CPUs
- Increased throughput for batch operations

## 4. Performance Metrics and Logging

Added performance metrics logging to identify bottlenecks:

```python
# At the end of scan_text function
scan_time = time.time() - start_time
print(f"Privacy scan completed in {scan_time:.4f}s: found {len(detected)} pattern types")
```

This helps identify slow patterns or processing bottlenecks.

## 5. Optional Dependencies

Document processing libraries are loaded conditionally:

```python
try:
    from pdfminer.high_level import extract_text_to_fp
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False
```

This ensures the application functions even when some document processing libraries are not available, with graceful fallbacks.

## 6. How to Enable These Optimizations

The optimizations are enabled by default in the latest version. To make use of the chunked file processing:

1. For direct file scanning from disk, use the new `scan_file_path` function:

```python
from privacy_scanner import scan_file_path

sensitive, detected, processing_time = scan_file_path(
    user_id=current_user_id,
    file_path="/path/to/file.pdf", 
    file_name="file.pdf",
    file_type="pdf"
)
```

2. For in-memory content, continue using the existing `scan_file_content` function:

```python
from privacy_scanner import scan_file_content

sensitive, detected = scan_file_content(
    user_id=current_user_id,
    file_content=content_string,
    file_name="example.txt"
)
```

## 7. Future Optimization Opportunities

- **NLP-assisted pattern detection**: Using spaCy to pre-filter text chunks before applying regex patterns
- **Pattern caching**: Implement caching of scan results for repeated text chunks
- **GPU acceleration**: For local LLM document processing
- **Adaptive chunk sizing**: Adjust chunk size based on available system memory and file characteristics
- **Distributed scanning**: For enterprise deployments with very high scanning volume

## 8. Benchmarking

To benchmark the performance improvements, compare the processing times for different file types:

```python
import time
from privacy_scanner import scan_text, scan_file_path

def benchmark_scan(file_path, file_type, user_id):
    # Benchmark old method (load entire file)
    with open(file_path, 'r', errors='ignore') as f:
        content = f.read()
    
    start_time = time.time()
    sensitive1, detected1 = scan_text(user_id, content)
    old_time = time.time() - start_time
    
    # Benchmark new method (chunked processing)
    start_time = time.time()
    sensitive2, detected2, _ = scan_file_path(user_id, file_path, file_path, file_type)
    new_time = time.time() - start_time
    
    print(f"File: {file_path}")
    print(f"Old method: {old_time:.4f}s, detected: {len(detected1)} pattern types")
    print(f"New method: {new_time:.4f}s, detected: {len(detected2)} pattern types")
    print(f"Speedup: {old_time/new_time:.2f}x")
```

## 9. Requirements

These optimizations require the following additional dependencies:

- **pdfminer.six**: For PDF text extraction
- **python-docx**: For Word document processing
- **openpyxl**: For Excel spreadsheet processing
- **concurrent-log-handler**: For thread-safe logging

These dependencies are included in the updated `pyproject.toml` file.
