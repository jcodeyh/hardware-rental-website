from flask import Blueprint, jsonify
from database import hardwareDB

hardware_bp = Blueprint("hardware", __name__)

# Route for getting all hardware names
@hardware_bp.route('/get_all_hw_names', methods=['GET'])
def get_all_hw_names():
    hardware_sets = hardwareDB.getAllHwNames()

    response = [
        {
            "hwName": hardware["hwName"],
            "capacity": hardware["capacity"],
            "availability": hardware["availability"],
        }
        for hardware in hardware_sets
    ]

    return jsonify(response), 200

# Route for getting hardware information
@hardware_bp.route('/get_hw_info', methods=['POST'])
def get_hw_info():
    # Extract data from request

    # Connect to MongoDB

    # Fetch hardware set information using the hardwareDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for checking out hardware
@hardware_bp.route('/check_out', methods=['POST'])
def check_out():
    # Extract data from request

    # Connect to MongoDB

    # Attempt to check out the hardware using the projectsDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for checking in hardware
@hardware_bp.route('/check_in', methods=['POST'])
def check_in():
    # Extract data from request

    # Connect to MongoDB

    # Attempt to check in the hardware using the projectsDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})

# Route for creating a new hardware set
@hardware_bp.route('/create_hardware_set', methods=['POST'])
def create_hardware_set():
    # Extract data from request

    # Connect to MongoDB

    # Attempt to create the hardware set using the hardwareDB module

    # Close the MongoDB connection

    # Return a JSON response
    return jsonify({})