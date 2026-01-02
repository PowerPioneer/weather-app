"""
Redis Caching Layer for Weather App
Provides shared caching across gunicorn workers with fallback to in-memory cache
"""

import json
import hashlib
from functools import wraps
from flask_caching import Cache

# Global cache instance (initialized in create_app)
cache = None

def init_cache(app):
    """
    Initialize Flask-Caching with Redis or simple in-memory cache.
    
    Args:
        app: Flask application instance
    """
    global cache
    
    # Import here to avoid circular imports
    from app.config import get_redis_url, get_redis_enabled
    
    redis_enabled = get_redis_enabled()
    
    if redis_enabled:
        try:
            from app.config import get_redis_url
            redis_url = get_redis_url()
            print(f"Initializing Redis cache: {redis_url}")
            
            cache = Cache(app, config={
                'CACHE_TYPE': 'RedisCache',
                'CACHE_REDIS_URL': redis_url,
                'CACHE_DEFAULT_TIMEOUT': 604800,  # 1 week default
                'CACHE_KEY_PREFIX': 'weather:',
                # Redis connection options
                'CACHE_OPTIONS': {
                    'socket_connect_timeout': 2,  # 2 second connection timeout
                    'socket_timeout': 2,  # 2 second operation timeout
                    'decode_responses': True,  # Auto-decode to strings
                }
            })
            
            # Test connection
            cache.set('_test_key', 'ok', timeout=5)
            if cache.get('_test_key') == 'ok':
                print("✅ Redis cache initialized successfully")
                cache.delete('_test_key')
                return True
            else:
                print("⚠️  Redis connection test failed, falling back to SimpleCache")
                redis_enabled = False
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("Falling back to in-memory SimpleCache")
            redis_enabled = False
    
    # Fallback to simple in-memory cache (single-process only)
    if not redis_enabled:
        print("Initializing in-memory cache (single-process only)")
        cache = Cache(app, config={
            'CACHE_TYPE': 'SimpleCache',
            'CACHE_DEFAULT_TIMEOUT': 604800,  # 1 week
        })
    
    return cache


def get_cache():
    """Get the global cache instance."""
    return cache


# Cache key generators
def geojson_country_key(month):
    """Generate cache key for country GeoJSON data."""
    return f"geojson:country:month:{month}"


def geojson_province_key(month):
    """Generate cache key for province GeoJSON data."""
    return f"geojson:province:month:{month}"


def weather_point_key(lat, lng, month):
    """
    Generate cache key for point weather data.
    Rounds coordinates to 4 decimal places (~11m precision).
    """
    lat_rounded = round(float(lat), 4)
    lng_rounded = round(float(lng), 4)
    return f"weather:point:{lat_rounded}:{lng_rounded}:{month}"


def grid_data_key(variable, month, bounds, resolution):
    """Generate cache key for grid data (hashed bounds to keep key short)."""
    bounds_str = f"{bounds['north']},{bounds['south']},{bounds['east']},{bounds['west']}"
    bounds_hash = hashlib.md5(bounds_str.encode()).hexdigest()[:8]
    return f"weather:grid:{variable}:{month}:{bounds_hash}:{resolution}"


# Helper functions for caching GeoJSON data
def get_cached_geojson(cache_key, loader_func):
    """
    Get GeoJSON from cache or load from disk.
    
    Args:
        cache_key: Redis cache key
        loader_func: Function to call if cache miss (loads from disk)
    
    Returns:
        dict: GeoJSON data
    """
    if cache is None:
        return loader_func()
    
    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data) if isinstance(cached_data, str) else cached_data
    
    # Cache miss - load from disk
    data = loader_func()
    if data:
        # Store in cache with 1 week TTL (or infinite for static data)
        try:
            cache.set(cache_key, json.dumps(data), timeout=604800)
        except Exception as e:
            print(f"Warning: Failed to cache data for {cache_key}: {e}")
    
    return data


def get_cached_weather_point(lat, lng, month, loader_func):
    """
    Get weather point data from cache or load from GeoTIFF.
    
    Args:
        lat: Latitude
        lng: Longitude
        month: Month (1-12)
        loader_func: Function to call if cache miss (reads GeoTIFF)
    
    Returns:
        dict: Weather data with tmin, tmax, prec, sunhours
    """
    if cache is None:
        return loader_func()
    
    cache_key = weather_point_key(lat, lng, month)
    
    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data) if isinstance(cached_data, str) else cached_data
    
    # Cache miss - load from GeoTIFF
    data = loader_func()
    if data:
        # Store in cache with infinite TTL (static climate data never changes)
        try:
            cache.set(cache_key, json.dumps(data), timeout=0)  # 0 = no expiration
        except Exception as e:
            print(f"Warning: Failed to cache weather point for {cache_key}: {e}")
    
    return data


def cache_decorator(key_func, timeout=604800):
    """
    Decorator for caching function results.
    
    Args:
        key_func: Function that generates cache key from function arguments
        timeout: Cache TTL in seconds (default: 1 week)
    
    Example:
        @cache_decorator(lambda month: f"data:{month}", timeout=3600)
        def load_data(month):
            return expensive_operation(month)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if cache is None:
                return func(*args, **kwargs)
            
            # Generate cache key from function arguments
            cache_key = key_func(*args, **kwargs)
            
            # Try cache first
            cached = cache.get(cache_key)
            if cached is not None:
                return json.loads(cached) if isinstance(cached, str) else cached
            
            # Cache miss - call function
            result = func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                try:
                    cache.set(cache_key, json.dumps(result), timeout=timeout)
                except Exception as e:
                    print(f"Warning: Failed to cache result for {cache_key}: {e}")
            
            return result
        
        return wrapper
    return decorator


def warm_cache_with_geojson(data_path, data_type='country'):
    """
    Pre-populate Redis cache with all GeoJSON files.
    
    Args:
        data_path: Path to data directory
        data_type: 'country' or 'province'
    
    Returns:
        int: Number of files cached
    """
    from pathlib import Path
    
    if cache is None:
        print("Cache not initialized")
        return 0
    
    aggregated_dir = Path(data_path) / data_type.lower() + 's' / 'aggregated'
    
    if not aggregated_dir.exists():
        print(f"Directory not found: {aggregated_dir}")
        return 0
    
    cached_count = 0
    
    # Load all monthly files
    for month in range(1, 13):
        if data_type == 'country':
            file_path = aggregated_dir / f"countries_month_{month:02d}.geojson"
            cache_key = geojson_country_key(month)
        else:
            file_path = aggregated_dir / f"provinces_month_{month:02d}.geojson"
            cache_key = geojson_province_key(month)
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cache.set(cache_key, json.dumps(data), timeout=0)  # No expiration
                cached_count += 1
                print(f"✓ Cached {data_type} data for month {month}")
            except Exception as e:
                print(f"✗ Failed to cache {file_path}: {e}")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    return cached_count


def get_cache_stats():
    """
    Get cache statistics (Redis specific).
    
    Returns:
        dict: Cache stats or None if not available
    """
    if cache is None:
        return {'status': 'not_initialized'}
    
    try:
        # Try to get Redis-specific stats
        if hasattr(cache.cache, '_client'):
            redis_client = cache.cache._client
            info = redis_client.info('stats')
            memory = redis_client.info('memory')
            
            return {
                'status': 'connected',
                'type': 'redis',
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'memory_used': memory.get('used_memory_human', 'unknown'),
                'keys': redis_client.dbsize(),
            }
        else:
            return {
                'status': 'active',
                'type': 'simple',
                'message': 'In-memory cache (stats not available)'
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def clear_cache(pattern=None):
    """
    Clear cache entries matching pattern.
    
    Args:
        pattern: Redis key pattern (e.g., 'geojson:country:*') or None for all
    
    Returns:
        int: Number of keys deleted
    """
    if cache is None:
        return 0
    
    try:
        if pattern:
            # Redis-specific pattern deletion
            if hasattr(cache.cache, '_client'):
                redis_client = cache.cache._client
                keys = list(redis_client.scan_iter(match=f"weather:{pattern}"))
                if keys:
                    return redis_client.delete(*keys)
                return 0
            else:
                # SimpleCache doesn't support pattern matching
                cache.clear()
                return -1
        else:
            # Clear all cache
            cache.clear()
            return -1
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return 0
