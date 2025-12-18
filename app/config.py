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
