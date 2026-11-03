import grpc
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from proto import projects_pb2, projects_pb2_grpc
from proto import hardware_pb2, hardware_pb2_grpc

app = FastAPI(title="Hardware Rental BFF", version="0.2.0")


class HardwareSelection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hardware_id: str = Field(alias="hardwareId", min_length=1)
    capacity: int = Field(gt=0)


class CreateProjectBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    creator_id: str = Field(alias="creatorId", min_length=1)
    project_id: str = Field(alias="projectId", min_length=1)
    project_name: str = Field(alias="projectName", min_length=1)
    project_desc: str | None = Field(default=None, alias="projectDesc")
    org_id: str = Field(alias="orgId", min_length=1)
    budget: int = Field(ge=0)
    hardware_list: list[HardwareSelection] = Field(default_factory=list, alias="hardwareList")


class ProjectMembershipBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId", min_length=1)
    org_id: str = Field(alias="orgId", min_length=1)
    user_id: str = Field(alias="userId", min_length=1)


def _channel(request: Request):
    channel = getattr(request.app.state, "grpc_channel", None)
    if channel is None:
        raise HTTPException(status_code=503, detail="BFF gRPC not started")
    return channel


def _grpc_error(error: grpc.aio.AioRpcError):
    mapping = {
        grpc.StatusCode.INVALID_ARGUMENT: 422,
        grpc.StatusCode.NOT_FOUND: 404,
        grpc.StatusCode.ALREADY_EXISTS: 409,
        grpc.StatusCode.FAILED_PRECONDITION: 409,
        grpc.StatusCode.UNAUTHENTICATED: 401,
        grpc.StatusCode.PERMISSION_DENIED: 403,
        grpc.StatusCode.RESOURCE_EXHAUSTED: 429,
        grpc.StatusCode.UNAVAILABLE: 503,
        grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    }
    status = mapping.get(error.code(), 502)
    raise HTTPException(status_code=status, detail=error.details() or error.code().name)


@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.post("/projects")
async def create_project(body: CreateProjectBody, request: Request):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    payload = projects_pb2.CreateProjectRequest(
        creator_id=body.creator_id,
        project_id=body.project_id,
        project_name=body.project_name,
        org_id=body.org_id,
        budget=body.budget,
        hardware_list=[
            projects_pb2.HardwareItem(
                hardware_id=item.hardware_id,
                capacity=item.capacity,
            )
            for item in body.hardware_list
        ],
    )
    if body.project_desc is not None:
        payload.project_desc = body.project_desc

    try:
        result = await stub.CreateProject(payload, timeout=30)
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"success": result.success, "errorMessage": result.error_message}


@app.post("/projects/join")
async def join_project(body: ProjectMembershipBody, request: Request):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    try:
        result = await stub.JoinProject(
            projects_pb2.ProjectMembershipRequest(
                project_id=body.project_id,
                org_id=body.org_id,
                user_id=body.user_id,
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"success": result.success, "errorMessage": result.error_message}


@app.post("/projects/leave")
async def leave_project(body: ProjectMembershipBody, request: Request):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    try:
        result = await stub.LeaveProject(
            projects_pb2.ProjectMembershipRequest(
                project_id=body.project_id,
                org_id=body.org_id,
                user_id=body.user_id,
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"success": result.success, "errorMessage": result.error_message}


@app.get("/projects")
async def list_projects(
    request: Request,
    projectId: str | None = None,
    orgId: str | None = None,
):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    args = {}
    if projectId is not None:
        args["project_id"] = projectId
    if orgId is not None:
        args["org_id"] = orgId
    try:
        result = await stub.SearchProjects(projects_pb2.SearchProjectsRequest(**args), timeout=30)
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"projectList": [
        {"projectId": p.project_id, "projectName": p.project_name, "orgId": p.org_id}
        for p in result.project_list
    ]}


@app.get("/projects/{project_id}")
async def get_project(request: Request, project_id: str, orgId: str = Query(min_length=1)):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    try:
        result = await stub.GetProject(
            projects_pb2.GetProjectRequest(project_id=project_id, org_id=orgId), timeout=30
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    p = result.project_info
    return {"projectInfo": {
        "projectId": p.project_id,
        "projectName": p.project_name,
        "projectDesc": p.project_desc,
        "creatorId": p.creator_id,
        "orgId": p.org_id,
        "budget": p.budget,
        "hardwareList": [
            {"hardwareId": x.hardware_id, "capacity": x.capacity} for x in p.hardware_list
        ],
        "joined_users": list(p.joined_users),
    }}


@app.get("/hardware")
async def list_hardware(
    request: Request,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    category: str = "",
    status: str = "",
):
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    try:
        result = await stub.ListHardware(
            hardware_pb2.ListHardwareRequest(
                page=page, size=size, category=category, status=status
            ), timeout=30
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {
        "items": [
            {
                "id": x.id, "name": x.name, "category": x.category,
                "assetTag": x.asset_tag, "status": x.status,
                "total": x.total, "out": x.out, "reserved": x.reserved,
                "version": x.version, "available": x.available,
            }
            for x in result.items
        ],
        "total": result.total, "page": result.page, "size": result.size,
    }
