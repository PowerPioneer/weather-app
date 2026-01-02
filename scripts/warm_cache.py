#!/usr/bin/env python3
"""
Warm Redis cache by pre-loading all GeoJSON files.
Run this script after deployment or Redis restart to eliminate cold-start delays.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set working directory to project root
os.chdir(Path(__file__).parent.parent)

def warm_cache():
    """Pre-populate Redis cache with all GeoJSON data."""
    print("=" * 60)
    print("REDIS CACHE WARMING SCRIPT")
    print("=" * 60)
    print()
    
    # Initialize Flask app to set up cache
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.cache import warm_cache_with_geojson, get_cache_stats, get_cache
        
        cache = get_cache()
        if cache is None:
            print("❌ Cache not initialized. Check Redis connection.")
            return False
        
        # Get initial cache stats
        print("Initial cache status:")
        stats = get_cache_stats()
        print(f"  Type: {stats.get('type', 'unknown')}")
        print(f"  Status: {stats.get('status', 'unknown')}")
        if stats.get('type') == 'redis':
            print(f"  Keys: {stats.get('keys', 0)}")
            print(f"  Memory: {stats.get('memory_used', 'unknown')}")
        print()
        
        # Warm cache with country data
        print("Loading country GeoJSON files...")
        data_path = Path(__file__).parent.parent / 'data'
        country_count = warm_cache_with_geojson(data_path, 'country')
        print(f"✅ Cached {country_count}/12 country files")
        print()
        
        # Warm cache with province data  
        print("Loading province GeoJSON files...")
        province_count = warm_cache_with_geojson(data_path, 'province')
        print(f"✅ Cached {province_count}/12 province files")
        print()
        
        # Get final cache stats
        print("Final cache status:")
        stats = get_cache_stats()
        if stats.get('type') == 'redis':
            print(f"  Keys: {stats.get('keys', 0)}")
            print(f"  Memory: {stats.get('memory_used', 'unknown')}")
        print()
        
        total_files = country_count + province_count
        if total_files == 24:
            print("=" * 60)
            print("✅ SUCCESS: All 24 GeoJSON files cached!")
            print("=" * 60)
            return True
        else:
            print("=" * 60)
            print(f"⚠️  WARNING: Only {total_files}/24 files cached")
            print("=" * 60)
            return False

if __name__ == '__main__':
    try:
        success = warm_cache()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
