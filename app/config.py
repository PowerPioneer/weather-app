"""
Configuration and API Key Management
Loads credentials from keys/config.py (not tracked in git)
"""

import os
import sys
from pathlib import Path

# Add keys directory to path so we can import config
KEYS_DIR = Path(__file__).parent.parent / 'keys'
if str(KEYS_DIR) not in sys.path:
    sys.path.insert(0, str(KEYS_DIR))

def load_config():
    """
    Load configuration from keys/config.py
    Falls back to environment variables if config.py doesn't exist
    """
    config = {
        'CDS_API_UID': None,
        'CDS_API_KEY': None,
        'FLASK_SECRET_KEY': None,
        'WEATHER_API_KEY': None,
    }
    
    config_file = KEYS_DIR / 'config.py'
    
    if config_file.exists():
        try:
            # Import the config module
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", config_file)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Load values from the config module
            for key in config.keys():
                if hasattr(config_module, key):
                    config[key] = getattr(config_module, key)
        except Exception as e:
            print(f"Warning: Could not load config from {config_file}: {e}")
    
    # Override with environment variables if they exist
    config['CDS_API_UID'] = os.getenv('CDS_API_UID', config['CDS_API_UID'])
    config['CDS_API_KEY'] = os.getenv('CDS_API_KEY', config['CDS_API_KEY'])
    config['FLASK_SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', config['FLASK_SECRET_KEY'])
    config['WEATHER_API_KEY'] = os.getenv('WEATHER_API_KEY', config['WEATHER_API_KEY'])
    
    return config

# Load config when module is imported
CONFIG = load_config()

# Feature flags for performance optimizations
USE_TOPOJSON = False  # Set to True to use TopoJSON format instead of GeoJSON (58% smaller files)
USE_COMBINED_ENDPOINT = True  # Set to True to use combined endpoint for all variables (reduces 4 API calls to 1)

def get_environment():
    """
    Determine the current environment (development or production).
    Checks FLASK_ENV environment variable, falls back to hostname detection.
    
    Returns:
        str: 'development' or 'production'
    """
    # Check explicit environment variable
    flask_env = os.getenv('FLASK_ENV', '').lower()
    if flask_env in ['production', 'prod']:
        return 'production'
    elif flask_env in ['development', 'dev']:
        return 'development'
    
    # Auto-detect based on hostname (localhost = development)
    import socket
    hostname = socket.gethostname().lower()
    if any(dev in hostname for dev in ['localhost', 'local', 'dev', 'desktop', 'laptop']):
        return 'development'
    
    # Default to production for safety
    return 'production'

def get_debug_mode():
    """
    Determine if Flask should run in debug mode.
    
    Returns:
        bool: True for debug mode, False otherwise
    """
    # Explicit override via environment variable
    flask_debug = os.getenv('FLASK_DEBUG', '').lower()
    if flask_debug in ['1', 'true', 'yes', 'on']:
        return True
    elif flask_debug in ['0', 'false', 'no', 'off']:
        return False
    
    # Otherwise, use environment to decide
    return get_environment() == 'development'

def get_cds_credentials():
    """Get CDS API credentials"""
    key = CONFIG.get('CDS_API_KEY')
    
    if not key or key.startswith('YOUR_'):
        raise ValueError(
            "CDS API key not configured. "
            "Please create keys/config.py with valid CDS credentials. "
            "See keys/config.example.py for template. "
            "Get your key from: https://cds.climate.copernicus.eu/how-to-api"
        )
    
    return key

def get_flask_secret_key():
    """Get Flask secret key"""
    secret = CONFIG.get('FLASK_SECRET_KEY')
    if not secret or secret.startswith('your-'):
        raise ValueError(
            "Flask secret key not configured. "
            "Please create keys/config.py with a secure secret key. "
            "See keys/config.example.py for template."
        )
    return secret

def get_weather_api_key():
    """Get Weather API key"""
    return CONFIG.get('WEATHER_API_KEY')

def get_redis_url():
    """
    Get Redis connection URL.
    
    Returns:
        str: Redis connection URL (default: redis://localhost:6379/0)
    """
    # Check for explicit Redis URL
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        return redis_url
    
    # Build from individual components
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = os.getenv('REDIS_PORT', '6379')
    redis_db = os.getenv('REDIS_DB', '0')
    redis_password = os.getenv('REDIS_PASSWORD', '')
    
    if redis_password:
        return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

def get_redis_enabled():
    """
    Check if Redis caching should be enabled.
    
    Returns:
        bool: True if Redis should be used, False otherwise
    """
    redis_enabled = os.getenv('REDIS_ENABLED', '').lower()
    if redis_enabled in ['1', 'true', 'yes', 'on']:
        return True
    elif redis_enabled in ['0', 'false', 'no', 'off']:
        return False
    
    # Auto-enable in production, optional in development
    return get_environment() == 'production'

