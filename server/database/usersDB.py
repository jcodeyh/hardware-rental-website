# Import necessary libraries and modules
from database.db import db
from werkzeug.security import generate_password_hash, check_password_hash
from database.errors import DuplicateUserError

'''
Structure of User entry:
User = {
    'username': username,
    'userId': userId,
    'password': password,
    'projects': [project1_ID, project2_ID, ...]
}
'''

# Function to add a new user
def addUser(client, username, password):
    password_hash = generate_password_hash(password)

    try:
        result = db.users.insert_one({
            'username': username,
            'password': password_hash,
            'projects': []
        })
    except Exception as e:
        # `from e` keeps the original pymongo error as __cause__ so the real
        # failure is still in the traceback, and uses `e` (silencing F841).
        raise DuplicateUserError(f"User already {username} exists") from e

    return str(result.inserted_id)

# Helper function to query a user by username and userId
def __queryUser(client, username):
    # Query and return a user from the database
    result = db.users.find_one({"username": username})
    if result:
        return result
    return None

def getUserByUsername(username):
    return db.users.find_one({"username": username})

# Function to log in a user
def login(client, username, password):
    # Authenticate a user and return login status
    user = __queryUser(client, username)
    if user and check_password_hash(user['password'], password):
        return user.get('username')
    return None

# Function to add a user to a project
def joinProject(client, userId, projectId):
    # Add a user to a specified project
    pass

# Function to get the list of projects for a user
def getUserProjectsList(client, userId):
    # Get and return the list of projects a user is part of
    pass

