from flask import Blueprint, request, jsonify, session
from bson.objectid import ObjectId

import database.projectsDB as projectsDB
import database.hardwareDB as hardwareDB
from database.usersDB import getUserByUsername


projects_bp = Blueprint("projects", __name__)

# Route for getting project information
@projects_bp.route("/get_project_info", methods=["GET"])
def get_project_info():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    # data = request.get_json()
    # project_id = data.get("projectId")
    project_id = request.args.get("projectId")

    project = projectsDB.queryProject(project_id)

    if project is None:
        return jsonify({"error": "Project not found"}), 404

    user = getUserByUsername(session["username"])

    if user["_id"] not in project["users"]:
        return jsonify({"error": "Forbidden"}), 403

    hardware_sets = hardwareDB.getAllHwNames()

    response = {
        "projectId": project["projectId"],
        "projectName": project["projectName"],
        "description": project["description"],
        "hwSets": project["hwSets"],
        "hardwareSets": [
            {
                "hwName": hardware["hwName"],
                "capacity": hardware["capacity"],
                "availability": hardware["availability"],
            }
            for hardware in hardware_sets
        ],
    }
    return jsonify(response), 200

# Route for creating a new project
@projects_bp.route('/create_project', methods=['POST'])
def create_project():
    # Extract data from request
    data = request.get_json()

    project_name = data.get('projectName')
    project_description = data.get('description')
    projectId = ObjectId()

    if project_name == "":
        return jsonify({"error": "Project must have a name"}), 411

    else:
        result = projectsDB.createProject(project_name, projectId, project_description)

    if result:
        return jsonify({"message": "Project created successfully"}), 200
    else:
        return jsonify({"error": "Project was not created"}), 500
# Route for joining a project
@projects_bp.route('/join_project', methods=['POST'])
def join_project():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    project_id = data.get("projectId")

    # Add the logged-in user to the project
    result = projectsDB.addUser(
        project_id,
        session["user_id"]
    )

    # No project matched the given projectId
    if result.matched_count == 0:
        return jsonify({"error": "Project not found"}), 404

    return jsonify({"message": "Project joined successfully"}), 200
