from flask import Blueprint, request, jsonify, session
from usersDB import addUser, login as user_login, joinProject, getUserProjectsList

authentication_bp = Blueprint('authentication', __name__)

# Route for user login
@authentication_bp.route('/login', methods=['POST'])
def login():
    # Extract data from request
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Connect to MongoDB

    # Attempt to log in the user using the usersDB module
    user_login(username, password)

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for user logout
@authentication_bp.route('/logout', methods=['POST'])
def logout():
    # Extract data from request
    data = request.get_json()

    # Connect to MongoDB

    # Attempt to log out the user (if necessary)

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for user signup
@authentication_bp.route('/signup', methods=['POST'])
def signup():
    # Extract data from request
    data = request.get_json()

    # Connect to MongoDB

    # Attempt to add the user using the usersDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

