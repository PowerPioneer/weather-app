import os
from flask import Flask, request
from flask_cors import CORS
from flask_compress import Compress
from app.config import get_flask_secret_key

def create_app():
    """Create and configure the Flask application."""
    # Get the parent directory (project root)
    basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create Flask app with explicit paths
    app = Flask(__name__,
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'),
                static_url_path='/static')
    
    # Load secret key from configuration
    try:
        app.config['SECRET_KEY'] = get_flask_secret_key()
    except ValueError as e:
        # Use a default for development, but warn
        print(f"Warning: {e}")
        app.config['SECRET_KEY'] = 'dev-key-change-in-production'
    
    # Configure compression
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'application/geo+json',
        'text/javascript'
    ]
    app.config['COMPRESS_LEVEL'] = 6  # Balance between speed and compression (1-9)
    app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress responses > 500 bytes
    
    # Configure static file caching and MIME types
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # No cache during development
    
    # Add response headers for proper static file serving
    @app.after_request
    def set_response_headers(response):
        # Use request.path instead of response.path
        if request.path.endswith('.css'):
            response.headers['Content-Type'] = 'text/css; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        elif request.path.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # Enable CORS and Compression
    CORS(app)
    Compress(app)
    
    # Register blueprints
    from app.routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    return app
