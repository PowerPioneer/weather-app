"""
Where to Go for Great Weather - Vacation Planning App with Interactive Weather Map
Main entry point for the Flask application.
"""

import os
from app import create_app

if __name__ == '__main__':
    # Ensure we're using the correct working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    app = create_app()
    # Debug mode is set in app.config by create_app() based on environment
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
