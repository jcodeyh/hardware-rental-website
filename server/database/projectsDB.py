# Import necessary libraries and modules
from database.db import db
import database.hardwareDB as hardwareDB
from bson import ObjectId

'''
Structure of Project entry:
Project = {
    'projectName': projectName,
    'projectId': projectId,
    'description': description,
    'hwSets': {HW1: 0, HW2: 10, ...},
    'users': [user1, user2, ...]
}
'''

# Function to query a project by its ID
def queryProject(projectId):
    # Query and return a project from the database
    return db.projects.find_one({"projectId": projectId})

# Function to create a new project
def createProject(projectName, projectId, description, creatorId=None):
    # Create a new project in the database
    # Ensure projectId is stored as a plain string for consistent querying
    try:
        users = [ObjectId(creatorId)] if creatorId else []
        db.projects.insert_one({
            "projectId": str(projectId),
            "projectName": projectName,
            "description": description,
            "hwSets": {},
            "users": users
        })
        return True
    except Exception as e:
        print("Error creating project:", e)
        return False

# Function to get all projects a specific user has joined or created
def getUserProjects(userId):
    try:
        return list(db.projects.find({"users": ObjectId(userId)}))
    except Exception as e:
        print("Error getting user projects:", e)
        return []

# Function to add a user to a project
def addUser(projectId, userId):
    result = db.projects.update_one({
            "projectId": projectId
    },
    {
        "$addToSet": { # adds a value to an array only if that value does not already exist
            "users": ObjectId(userId)
        }
    })

    return result

# Function to update hardware usage in a project
def updateUsage(client, projectId, hwSetName):
    pass

# Function to check out hardware for a project
def checkOutHW(projectId, hwSetName, qty):
    # Try to reserve the requested hardware
    result = hardwareDB.reserveHardware(hwSetName, qty)

    # If no document was updated, there was not enough availability
    if result.matched_count == 0:
        return False

    db.projects.update_one(
        {
            "projectId": projectId
        },
        {
            "$inc": {
                f"hwSets.{hwSetName}": qty
            }
        }
    )

    return True

# Function to check in hardware for a project
def checkInHW(projectId, hwSetName, qty):
    # Decrease the amount held by the project only if it holds enough
    result = db.projects.update_one(
        {
            "projectId": projectId,
            f"hwSets.{hwSetName}": {"$gte": qty}
        },
        {
            "$inc": {
                f"hwSets.{hwSetName}": -qty
            }
        }
    )

    if result.matched_count == 0:
        return False

    hardwareDB.releaseHardware(hwSetName, qty)

    return True
