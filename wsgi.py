import os
from app import create_app

os.chdir(os.path.dirname(os.path.abspath(__file__)))
app = create_app()
