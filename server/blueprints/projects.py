from flask import Blueprint, request, jsonify, session
from bson.objectid import ObjectId
from database.db import db

import database.projectsDB as projectsDB
import database.hardwareDB as hardwareDB
from database.usersDB import getUserByUsername


projects_bp = Blueprint("projects", __name__)

# Route for getting user's joined/created projects
@projects_bp.route("/get_user_projects_list", methods=["GET", "POST"])
def get_user_projects_list():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    user_projects = projectsDB.getUserProjects(user_id)

    # Serialize ObjectId fields for JSON
    for p in user_projects:
        p['_id'] = str(p['_id'])
        p['projectId'] = str(p.get('projectId', ''))
        p['users'] = [str(u) for u in p.get('users', [])]

    return jsonify(user_projects), 200


# Route for getting project information
@projects_bp.route("/get_project_info", methods=["GET"])
def get_project_info():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized - Please log in"}), 401

    project_id = request.args.get("projectId")
    project = projectsDB.queryProject(project_id)

    if project is None:
        return jsonify({"error": "Project not found"}), 404

    # Verify that the logged-in user has joined/created this project
    user = getUserByUsername(session.get("username"))
    if not user or user["_id"] not in project.get("users", []):
        return jsonify({"error": "Forbidden - You have not joined this project"}), 403

    hardware_sets = hardwareDB.getAllHwNames()

    response = {
        "projectId": project.get("projectId"),
        "projectName": project.get("projectName"),
        "description": project.get("description", ""),
        "hwSets": project.get("hwSets", {}),
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
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    project_id = data.get('projectId', '').strip()
    project_name = data.get('projectName', '').strip()

    if not project_name:
        return jsonify({"error": "Project must have a name"}), 400

    if not project_id:
        project_id = str(ObjectId())  # auto-generate if not provided

    # Check for duplicate projectId
    if db.projects.find_one({'projectId': project_id}):
        return jsonify({'error': 'A project with that ID already exists'}), 409

    # Pass the creator's user_id from session so they are automatically added to users array
    creator_id = session.get("user_id")
    result = projectsDB.createProject(project_name, project_id, data.get('description', ''), creatorId=creator_id)

    if result:
        return jsonify({"message": "Project created successfully", "projectId": project_id}), 201
    else:
        return jsonify({"error": "Project was not created"}), 500


# Route for joining a project
@projects_bp.route('/join_project', methods=['POST'])
def join_project():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    project_id = data.get("projectId")

    if not project_id:
        return jsonify({"error": "projectId is required"}), 400

    # Add the logged-in user to the project's users array
    result = projectsDB.addUser(
        project_id,
        session["user_id"]
    )

    # No project matched the given projectId
    if result.matched_count == 0:
        return jsonify({"error": "Project not found"}), 404

    return jsonify({"message": "Project joined successfully"}), 200
    return jsonify(response), 200
