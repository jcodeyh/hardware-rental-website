
from proto import projects_pb2 as pb


def create_to_json(request, hardware_field="capacity"):
    hardware_list = []

    for item in request.hardware_list:
        quantity = item.allocation
        hardware_list.append({
            "hardwareId": item.hardware_id,
            "allocation": quantity,
            "capacity": quantity,
        })

    return {
        "creatorId": request.creator_id,
        "projectId": request.project_id,
        "projectName": request.project_name,
        "projectDesc": (
            request.project_desc
            if request.HasField("project_desc")
            else ""
        ),
        "orgId": request.org_id,
        "budget": request.budget,
        "hardwareList": hardware_list,
    }


def membership_to_json(request):
    return {
        "projectId": request.project_id,
        "orgId": request.org_id,
        "userId": request.user_id,
    }


def search_to_json(request):
    result = {}

    if request.HasField("project_id"):
        result["projectId"] = request.project_id

    if request.HasField("org_id"):
        result["orgId"] = request.org_id

    return result


def summary_to_proto(data):
    return pb.ProjectSummary(
        project_id=data["projectId"],
        project_name=data["projectName"],
        org_id=data["orgId"],
    )


def project_to_proto(data):
    return pb.Project(
        project_id=data["projectId"],
        project_name=data["projectName"],
        project_desc=data.get("projectDesc") or "",
        creator_id=data.get("creatorId", ""),
        org_id=data["orgId"],
        budget=data.get("budget", 0),
        hardware_list=[
            pb.HardwareItem(
                hardware_id=item["hardwareId"],
                allocation=item.get("allocation", item.get("capacity", 0)),
            )
            for item in data.get("hardwareList", [])
        ],
        joined_users=data.get("joined_users", []),
    )


def budget_context_to_json(request):
    return {
        "orgId": request.org_id,
        "budget": request.budget,
        "items": [
            {"description": item.description, "quantity": item.quantity}
            for item in request.items
        ],
    }
