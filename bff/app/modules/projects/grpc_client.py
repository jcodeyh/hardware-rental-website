import grpc
from google.protobuf import json_format

from proto.upstream import projects_pb2 as pb
from proto.upstream import projects_pb2_grpc as pb_grpc


def _summary_json(item):
    return {
        "projectId": item.project_id,
        "projectName": item.project_name,
        "orgId": item.org_id,
        "joined_users": list(item.joined_users),
    }


def _project_json(project):
    return {
        "projectId": project.project_id,
        "projectName": project.project_name,
        "projectDesc": project.project_desc,
        "creatorId": project.creator_id,
        "orgId": project.org_id,
        "budget": project.budget,
        "hardwareList": [
            {"hardwareId": item.hardware_id, "allocation": item.allocation}
            for item in project.hardware_list
        ],
        "joined_users": list(project.joined_users),
    }


def _price_json(message):
    return json_format.MessageToDict(message, always_print_fields_with_no_presence=True)


class ProjectsGrpcClient:
    def __init__(self, target: str, timeout: float = 60.0, use_tls: bool = False, channel=None):
        if not target.strip():
            raise ValueError("PROJECTS_GRPC_TARGET is required")

        if channel is not None:
            self.channel = channel
        elif use_tls:
            self.channel = grpc.aio.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            self.channel = grpc.aio.insecure_channel(target)

        self.timeout = timeout
        self.stub = pb_grpc.ProjectsServiceStub(self.channel)

    async def _call(self, method, request):
        return await method(request, timeout=self.timeout)

    async def create_project(self, data: dict) -> dict:
        await self._call(self.stub.CreateProject, pb.CreateProjectRequest(
            org_id=data["orgId"],
            project_id=data["projectId"],
            project_name=data["projectName"],
            project_desc=data.get("projectDesc") or "",
            creator_id=data["creatorId"],
            budget=data["budget"],
            hardware_list=[
                pb.HardwareItem(hardware_id=item["hardwareId"], allocation=item["allocation"])
                for item in data.get("hardwareList", [])
            ],
        ))
        return {"success": True}

    async def _membership(self, method, data: dict) -> dict:
        await self._call(method, pb.MembershipRequest(
            org_id=data["orgId"],
            project_id=data["projectId"],
            user_id=data["userId"],
        ))
        return {"success": True}

    async def join_project(self, data: dict) -> dict:
        return await self._membership(self.stub.JoinProject, data)

    async def leave_project(self, data: dict) -> dict:
        return await self._membership(self.stub.LeaveProject, data)

    async def search_projects(self, filters: dict) -> dict:
        request = pb.SearchProjectsRequest()
        if filters.get("orgId"):
            request.org_id = filters["orgId"]
        if filters.get("projectId"):
            request.project_id = filters["projectId"]
        if filters.get("userId"):
            request.user_id = filters["userId"]
        result = await self._call(self.stub.SearchProjects, request)
        return {"projectList": [_summary_json(item) for item in result.project_list]}

    async def get_project(self, project_id: str, org_id: str) -> dict:
        result = await self._call(
            self.stub.GetProject,
            pb.GetProjectRequest(project_id=project_id, org_id=org_id),
        )
        return {"projectInfo": _project_json(result.project_info)}

    async def get_unit_price(self, category: str) -> dict:
        result = await self._call(self.stub.GetUnitPrice, pb.GetUnitPriceRequest(category=category))
        return _price_json(result)

    async def get_department_spend(self, keyword: str) -> dict:
        result = await self._call(
            self.stub.GetDepartmentSpend, pb.GetDepartmentSpendRequest(keyword=keyword)
        )
        return _price_json(result)

    async def get_budget_context(self, data: dict) -> dict:
        result = await self._call(self.stub.GetBudgetContext, pb.GetBudgetContextRequest(
            org_id=data["orgId"],
            budget=data["budget"],
            items=[
                pb.BudgetItem(description=item["description"], quantity=item["quantity"])
                for item in data["items"]
            ],
        ))
        return _price_json(result)

    async def close(self) -> None:
        await self.channel.close()
