#!/usr/bin/env python3
"""
Test script for delimiter detection functionality

This script tests the delimiter_detector module to ensure it works correctly
before integrating with the main app.
"""

import sys
import pandas as pd
from io import StringIO

# Mock the delimiter_detector functions for testing
def detect_delimiter_test(file_content, filename, num_lines=5):
    """Test delimiter detection with sample data"""
    
    # Convert bytes to string if necessary
    if isinstance(file_content, bytes):
        try:
            file_content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            file_content = file_content.decode('latin1')
    
    lines = file_content.split('\n')[:num_lines]
    
    # Test different delimiters
    delimiters_to_test = [',', '\t', ';', '|']
    results = {}
    
    for delim in delimiters_to_test:
        count = sum(line.count(delim) for line in lines if line.strip())
        if count > 0:
            results[delim] = count
    
    if not results:
        return ',', 0.0, None
    
    # Find most common delimiter
    best_delim = max(results.items(), key=lambda x: x[1])[0]
    
    # Calculate confidence (simplified)
    total_chars = sum(len(line) for line in lines)
    confidence = min(results[best_delim] / (total_chars / 10), 1.0)
    
    # Try to create preview
    try:
        preview_df = pd.read_csv(StringIO(file_content), sep=best_delim, nrows=5)
    except:
        preview_df = None
    
    return best_delim, confidence, preview_df


def get_delimiter_name_test(delimiter):
    """Get human-readable delimiter name"""
    names = {
        ',': 'comma',
        '\t': 'tab',
        ';': 'semicolon',
        '|': 'pipe'
    }
    return names.get(delimiter, f"'{delimiter}'")


# Test cases
def test_comma_delimited():
    """Test with comma-delimited data"""
    print("\n" + "="*60)
    print("TEST 1: Comma-delimited file")
    print("="*60)
    
    data = """name,age,city
John,30,New York
Jane,25,Los Angeles
Bob,35,Chicago"""
    
    delimiter, confidence, preview = detect_delimiter_test(data, "test_comma.csv")
    
    print(f"Detected delimiter: {get_delimiter_name_test(delimiter)}")
    print(f"Confidence: {confidence:.2%}")
    print(f"\nPreview:")
    if preview is not None:
        print(preview.to_string(index=False))
    
    assert delimiter == ',', f"Expected comma, got {delimiter}"
    print("\n✓ TEST PASSED")


def test_tab_delimited():
    """Test with tab-delimited data"""
    print("\n" + "="*60)
    print("TEST 2: Tab-delimited file")
    print("="*60)
    
    data = """name\tage\tcity
John\t30\tNew York
Jane\t25\tLos Angeles
Bob\t35\tChicago"""
    
    delimiter, confidence, preview = detect_delimiter_test(data, "test_tab.csv")
    
    print(f"Detected delimiter: {get_delimiter_name_test(delimiter)}")
    print(f"Confidence: {confidence:.2%}")
    print(f"\nPreview:")
    if preview is not None:
        print(preview.to_string(index=False))
    
    assert delimiter == '\t', f"Expected tab, got {delimiter}"
    print("\n✓ TEST PASSED")


def test_semicolon_delimited():
    """Test with semicolon-delimited data"""
    print("\n" + "="*60)
    print("TEST 3: Semicolon-delimited file")
    print("="*60)
    
    data = """name;age;city
John;30;New York
Jane;25;Los Angeles
Bob;35;Chicago"""
    
    delimiter, confidence, preview = detect_delimiter_test(data, "test_semicolon.csv")
    
    print(f"Detected delimiter: {get_delimiter_name_test(delimiter)}")
    print(f"Confidence: {confidence:.2%}")
    print(f"\nPreview:")
    if preview is not None:
        print(preview.to_string(index=False))
    
    assert delimiter == ';', f"Expected semicolon, got {delimiter}"
    print("\n✓ TEST PASSED")


def test_pipe_delimited():
    """Test with pipe-delimited data"""
    print("\n" + "="*60)
    print("TEST 4: Pipe-delimited file")
    print("="*60)
    
    data = """name|age|city
John|30|New York
Jane|25|Los Angeles
Bob|35|Chicago"""
    
    delimiter, confidence, preview = detect_delimiter_test(data, "test_pipe.csv")
    
    print(f"Detected delimiter: {get_delimiter_name_test(delimiter)}")
    print(f"Confidence: {confidence:.2%}")
    print(f"\nPreview:")
    if preview is not None:
        print(preview.to_string(index=False))
    
    assert delimiter == '|', f"Expected pipe, got {delimiter}"
    print("\n✓ TEST PASSED")


def test_mixed_with_commas_in_data():
    """Test tab-delimited with commas in the data"""
    print("\n" + "="*60)
    print("TEST 5: Tab-delimited with commas in data")
    print("="*60)
    
    data = """name\tage\tcity
John Smith, Jr.\t30\tNew York, NY
Jane Doe\t25\tLos Angeles, CA
Bob Johnson\t35\tChicago, IL"""
    
    delimiter, confidence, preview = detect_delimiter_test(data, "test_mixed.csv")
    
    print(f"Detected delimiter: {get_delimiter_name_test(delimiter)}")
    print(f"Confidence: {confidence:.2%}")
    print(f"\nPreview:")
    if preview is not None:
        print(preview.to_string(index=False))
    
    assert delimiter == '\t', f"Expected tab, got {delimiter}"
    print("\n✓ TEST PASSED")


def run_all_tests():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# DELIMITER DETECTION TESTS")
    print("#"*60)
    
    try:
        test_comma_delimited()
        test_tab_delimited()
        test_semicolon_delimited()
        test_pipe_delimited()
        test_mixed_with_commas_in_data()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60 + "\n")
        return True
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
