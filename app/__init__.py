import os
from flask import Flask
from flask_cors import CORS

def create_app():
    """Create and configure the Flask application."""
    # Get the parent directory (project root)
    basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create Flask app with explicit paths
    app = Flask(__name__,
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'))
    
    CORS(app)
    
    # Register blueprints
    from app.routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    return app
