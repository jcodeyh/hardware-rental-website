
from proto import projects_pb2 as pb


def create_to_json(request):
    return {
        "projectId": request.project_id,
        "projectName": request.project_name,
        "projectDesc": (
            request.project_desc
            if request.HasField("project_desc")
            else ""
        ),
        "projectCreatorId": request.project_creator_id,
        "budget": request.budget,
        "hardwareList": [
            {
                "hardwareId": item.hardware_id,
                "hardwareName": item.hardware_name,
                "capacity": item.capacity,
            }
            for item in request.hardware_list
        ],
    }


def membership_to_json(request):
    return {
        "projectId": request.project_id,
        "projectCreatorId": request.project_creator_id,
        "userId": request.user_id,
    }


def search_to_json(request):
    result = {}

    if request.HasField("project_id"):
        result["projectId"] = request.project_id

    if request.HasField("project_creator_id"):
        result["projectCreatorId"] = request.project_creator_id

    return result


def project_to_proto(data):
    return pb.Project(
        project_id=data["projectId"],
        project_name=data["projectName"],
        project_desc=data.get("projectDesc") or "",
        project_creator_id=data["projectCreatorId"],
        budget=data["budget"],
        hardware_list=[
            pb.HardwareItem(
                hardware_id=item["hardwareId"],
                hardware_name=item["hardwareName"],
                capacity=item["capacity"],
            )
            for item in data.get("hardwareList", [])
        ],
        joined_users=data.get("joined_users", []),
    )


def summary_to_proto(data):
    return pb.ProjectSummary(
        project_id=data["projectId"],
        project_name=data["projectName"],
        project_creator_id=data["projectCreatorId"],
    )
