from flask import Blueprint, request, jsonify

import database.projectsDB as projectsDB
import database.hardwareDB as hardwareDB


projects_bp = Blueprint("projects", __name__)

# Route for getting project information
@projects_bp.route("/get_project_info", methods=["GET"])
def get_project_info():
    data = request.get_json()
    project_id = data.get("projectId")

    project = projectsDB.queryProject(project_id)

    if project is None:
        return jsonify({"error": "Project not found"}), 404

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