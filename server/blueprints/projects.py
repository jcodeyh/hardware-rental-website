from flask import Blueprint, request, jsonify

import database.projectsDB as projectsDB


projects_bp = Blueprint("projects", __name__)

# Route for getting project information
@projects_bp.route('/get_project_info', methods=['POST'])
def get_project_info():
    data = request.get_json()
    projectId = data.get("projectId")
    project = projectsDB.queryProject(projectId)

    if project is None:
        return jsonify({"Project not found."}), 404

    response = {
        "projectId": project["projectId"],
        "projectName": project["projectName"],
        "description": project["description"],
        "hwSets": project["hwSets"],
        "users": [str(user_id) for user_id in project["users"]],
    }
    return jsonify(response), 200