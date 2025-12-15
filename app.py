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
    app.run(debug=True, host='0.0.0.0', port=5000)
