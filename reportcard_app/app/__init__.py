from flask import Flask
import os
import logging

# Create the Flask application instance
app = Flask(__name__)

# --- UPDATED SECTION ---
# Configure logging
logging.basicConfig(level=logging.INFO)
# Load the secret key from an environment variable
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# -----------------------

# Configuration for the upload folder
upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'uploads')
os.makedirs(upload_folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = upload_folder

# Import the routes to register them with the application
from app import routes
