# Import libraries and modules
from os import getenv

from flask import Flask, jsonify
from flask_cors import CORS
from database.db import init_indexes, db
from config import Config

# Import custom modules
from blueprints.authentication import authentication_bp
from blueprints.projects import projects_bp
from blueprints.hardware import hardware_bp


# Initialize Flask
app = Flask(__name__)

# Origins allowed to call this API, comma-separated.
# Supports both 5173 (Vite default) and 8080
allowed_origins = [
    o.strip()
    for o in getenv("CORS_ORIGINS", "http://localhost:5173, http://localhost:8080").split(",")
    if o.strip()
]

CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)

app.register_blueprint(authentication_bp)  # Register the authentication blueprint
app.register_blueprint(projects_bp)  # Register the projects blueprint
app.register_blueprint(hardware_bp)  # Register the hardware blueprint

app.secret_key = Config().session_pass  # Set secret key for session management

cross_site_session = getenv("CROSS_SITE_SESSION", "false").lower() == "true"
app.config.update(
    SESSION_COOKIE_SAMESITE="None" if cross_site_session else "Lax",
    SESSION_COOKIE_SECURE=cross_site_session,
    SESSION_COOKIE_HTTPONLY=True,  # JS can't read it; blocks cookie theft via XSS
)


init_indexes()  # Ensure required indexes exist; runs once at app startup, not on every import

# Route for the main page
@app.route('/main')
def mainPage():
    return jsonify({})

# Route for checking the inventory of projects
# NOTE: /create_project, /join_project, and /get_user_projects_list are handled by projects_bp
@app.route('/api/inventory', methods=['GET'])
def check_inventory():
    try:
        projects = list(db.projects.find({}))
        # Serialize ObjectId fields so JSON can encode them
        for p in projects:
            p['_id'] = str(p['_id'])
            if hasattr(p.get('projectId'), '__class__') and p['projectId'].__class__.__name__ == 'ObjectId':
                p['projectId'] = str(p['projectId'])
            p['users'] = [str(u) for u in p.get('users', [])]
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Main entry point for the application — configured on port 8000
if __name__ == '__main__':
    init_indexes()
    app.run(debug=True, port=8000)
