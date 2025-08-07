from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import logging
import click

# --- Database Setup ---
# Get the base directory of the reportcard_app
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load the secret key from an environment variable
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Configure the database URI and disable a SQLAlchemy feature we don't need
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '..', 'data', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# --------------------

# Configuration for the upload folder
upload_folder = os.path.join(basedir, '..', 'data', 'uploads')
os.makedirs(upload_folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = upload_folder

# Import routes and models after app and db are created
from app import routes, models

@app.cli.command("init-db")
def init_db_command():
    """Creates the database tables."""
    with app.app_context():
        db.create_all()
    print("Initialized the database.")

