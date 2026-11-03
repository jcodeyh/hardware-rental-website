import grpc
from fastapi import FastAPI, HTTPException, Query, Request
from proto import projects_pb2, projects_pb2_grpc
from proto import hardware_pb2, hardware_pb2_grpc

app = FastAPI(title="Hardware Rental BFF", version="0.1.0")


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
