# Import necessary libraries and modules
from database.db import db
'''
Structure of Hardware Set entry:
HardwareSet = {
    'hwName': hwSetName,
    'capacity': initCapacity,
    'availability': initCapacity
}
'''

def reserveHardware(hwSetName, qty):
    return db.hardware.update_one(
        {
            "hwName": hwSetName,
            "availability": {"$gte": qty} # Update if the availability is greater than or equal to the quantity.
        },
        {
            "$inc": { # Increase a value
                "availability": -qty
            }
        }
    )

# Function to create a new hardware set
def createHardwareSet(client, hwSetName, initCapacity):
    # Create a new hardware set in the database
    pass

# Function to query a hardware set by its name
def queryHardwareSet(client, hwSetName):
    # Query and return a hardware set from the database
    pass

# Function to update the availability of a hardware set
def updateAvailability(client, hwSetName, newAvailability):
    # Update the availability of an existing hardware set
    pass

# Function to request space from a hardware set
def requestSpace(client, hwSetName, amount):
    # Request a certain amount of hardware and update availability
    pass

# Function to get all hardware set names
def getAllHwNames():
    return list(db.hardware.find({}))
