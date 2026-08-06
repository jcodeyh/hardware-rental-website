# Import libraries and modules
from os import getenv

from flask import Flask, jsonify
from flask_cors import CORS
from database.db import init_indexes
from config import Config

# Import custom modules
from blueprints.authentication import authentication_bp
from blueprints.projects import projects_bp
from blueprints.hardware import hardware_bp


# Initialize Flask
app = Flask(__name__)
# Origins allowed to call this API, comma-separated.

allowed_origins = [
    o.strip()
    for o in getenv("CORS_ORIGINS", "http://localhost:8080").split(",")
    if o.strip()
]

CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)

# cors = CORS(app, resources={r"/*": {"origins": "*"}})  # allow the client to call this API
# app.config['CORS_HEADERS'] = 'Content-Type'

app.register_blueprint(authentication_bp)  # Register the authentication blueprint
app.register_blueprint(projects_bp)  # Register the projects blueprint
app.register_blueprint(hardware_bp)  # Register the hardware blueprint

app.secret_key = Config().session_pass  # Set secret key for session management

# In Azure the client and API are on different hosts, so the session cookie is
# cross-site. Browsers only send a cross-site cookie when it is SameSite=None
# AND Secure -- and they reject SameSite=None without Secure outright.
# Locally both run on localhost (same site, plain http), where Lax is correct
# and Secure would stop the cookie being set at all. Hence the env switch.
cross_site_session = getenv("CROSS_SITE_SESSION", "false").lower() == "true"
app.config.update(
    SESSION_COOKIE_SAMESITE="None" if cross_site_session else "Lax",
    SESSION_COOKIE_SECURE=cross_site_session,
    SESSION_COOKIE_HTTPONLY=True,  # JS can't read it; blocks cookie theft via XSS
)


init_indexes()  # Ensure required indexes exist; runs once at app startup, not on every import

# Route for the main page (Work in progress)
@app.route('/main')
def mainPage():
    # Extract data from request

    # Connect to MongoDB

    # Fetch user projects using the usersDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for joining a project
@app.route('/join_project', methods=['POST'])
def join_project():
    # Extract data from request

    # Connect to MongoDB

    # Attempt to join the project using the usersDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for adding a new user
@app.route('/add_user', methods=['POST'])
def add_user():
    # Extract data from request

    # Connect to MongoDB

    # Attempt to add the user using the usersDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for getting the list of user projects
@app.route('/get_user_projects_list', methods=['POST'])
def get_user_projects_list():
    # Extract data from request

    # Connect to MongoDB

    # Fetch the user's projects using the usersDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for checking the inventory of projects
@app.route('/api/inventory', methods=['GET'])
def check_inventory():
    # Connect to MongoDB

    # Fetch all projects from the HardwareCheckout.Projects collection

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Main entry point for the application
if __name__ == '__main__':
    init_indexes()  # Ensure required indexes exist; runs once at app startup, not on every import
    app.run()


