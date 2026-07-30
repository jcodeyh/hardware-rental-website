from flask import Blueprint, request, jsonify, session
from database.usersDB import addUser, login as user_login, joinProject, getUserProjectsList
from database.db import client
from database.errors import DuplicateUserError

authentication_bp = Blueprint('authentication', __name__)

# Route for user login
@authentication_bp.route('/login', methods=['POST'])
def login():
    # Extract data from request
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Attempt to log in
    result  = user_login(client, username, password) # type error 

    if result is None:
        return jsonify({"error": "Invalid username or password"}), 401

    # Return a JSON response
    return jsonify({"data": result}), 200

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
    username = data.get('username')
    password = data.get('password')

    # Attempt to add the user
    try:
        user_id = addUser(client, username, password)
    except DuplicateUserError:
        return jsonify({"error": "User already taken"}), 409

    # Return a JSON response
    return jsonify({"user_id": user_id}), 201

