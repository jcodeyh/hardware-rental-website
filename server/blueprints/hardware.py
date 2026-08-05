from flask import Blueprint, jsonify, request, session
from database import hardwareDB, projectsDB, usersDB

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
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Extract data from request
    data = request.get_json()

    project_id = data.get("projectId")
    hw_set_name = data.get("hwSetName")
    qty = data.get("qty")

    if not isinstance(qty, int) or qty < 1:
        return jsonify({"error": "Quantity must be a positive integer"}), 400

    project = projectsDB.queryProject(project_id)
    #make sure the project exists
    if project is None:
        return jsonify({"error": "Project not found"}), 404

    user = usersDB.getUserByUsername(session["username"])

    if user["_id"] not in project["users"]:
        return jsonify({"error": "Forbidden"}), 403

    # Attempt to check out the hardware
    success = projectsDB.checkOutHW(
        project_id,
        hw_set_name,
        qty,
    )

    if not success:
        return jsonify({"error": "Not enough hardware available"}), 409

    return jsonify({"message": "Hardware checked out successfully"}), 200

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