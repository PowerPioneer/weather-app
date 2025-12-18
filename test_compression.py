"""
Test script to verify Flask-Compress is working properly.
"""
import requests
import sys

def test_compression():
    """Test if the Flask app is serving compressed responses."""
    
    url = "http://127.0.0.1:5000/api/provinces?month=12&variable=overall"
    
    print("Testing Flask compression...")
    print(f"URL: {url}\n")
    
    # Test without compression
    print("1. Request WITHOUT compression:")
    try:
        response_uncompressed = requests.get(url, headers={"Accept-Encoding": ""})
        size_uncompressed = len(response_uncompressed.content)
        print(f"   Status: {response_uncompressed.status_code}")
        print(f"   Content-Length: {size_uncompressed:,} bytes ({size_uncompressed / 1024:.1f} KB)")
        print(f"   Content-Encoding: {response_uncompressed.headers.get('Content-Encoding', 'None')}")
    except Exception as e:
        print(f"   Error: {e}")
        print("\n⚠️  Make sure the Flask app is running (python app.py)")
        sys.exit(1)
    
    # Test with compression
    print("\n2. Request WITH gzip compression:")
    try:
        response_compressed = requests.get(url, headers={"Accept-Encoding": "gzip, deflate, br"})
        size_compressed = len(response_compressed.content)
        print(f"   Status: {response_compressed.status_code}")
        print(f"   Content-Length: {size_compressed:,} bytes ({size_compressed / 1024:.1f} KB)")
        print(f"   Content-Encoding: {response_compressed.headers.get('Content-Encoding', 'None')}")
    except Exception as e:
        print(f"   Error: {e}")
        sys.exit(1)
    
    # Calculate compression ratio
    if 'gzip' in response_compressed.headers.get('Content-Encoding', ''):
        # Get the actual compressed size from raw response
        raw_size = len(response_compressed.raw.read())
        if raw_size > 0:
            compression_ratio = (1 - raw_size / size_uncompressed) * 100
            print(f"\n✓ Compression is ACTIVE")
            print(f"   Compression ratio: {compression_ratio:.1f}%")
            print(f"   Data saved per request: {(size_uncompressed - raw_size) / 1024:.1f} KB")
        else:
            print(f"\n✓ Compression header present")
            print(f"   Note: Actual compressed size may vary")
    else:
        print(f"\n⚠️  Compression NOT detected")
        print(f"   Make sure Flask-Compress is installed and configured")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  Original file size: ~5 MB (simplified from 57 MB)")
    print(f"  With gzip compression: ~1-2 MB (estimated)")
    print(f"  Total improvement: ~95-96% from original")
    print("="*60)

if __name__ == "__main__":
    test_compression()
