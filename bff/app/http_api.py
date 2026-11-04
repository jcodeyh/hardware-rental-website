import asyncio
import logging
import secrets
from typing import Literal

import grpc
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from proto import projects_pb2, projects_pb2_grpc
from proto import hardware_pb2, hardware_pb2_grpc
from proto import users_pb2, users_pb2_grpc

logger = logging.getLogger(__name__)

SERVICE_ID_PATTERN = r"^[A-Za-z0-9_.:@-]{1,64}$"
REQUEST_ID_PATTERN = r"^[A-Za-z0-9_:-]{1,60}$"
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60

settings = get_settings()

app = FastAPI(title="Hardware Rental BFF", version="0.3.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret or secrets.token_urlsafe(32),
    session_cookie="haas_session",
    max_age=SESSION_MAX_AGE_SECONDS,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)


class SignUpBody(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,40}$")
    password: str = Field(min_length=8, max_length=200)
    agency_code: Literal["AUS", "DAL", "TEX"] = Field(alias="agencyCode")


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class HardwareSelection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hardware_id: str = Field(alias="hardwareId", min_length=1)
    capacity: int = Field(gt=0)


class CreateProjectBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId", pattern=SERVICE_ID_PATTERN)
    project_name: str = Field(alias="projectName", min_length=1)
    project_desc: str | None = Field(default=None, alias="projectDesc")
    budget: int = Field(ge=0)
    hardware_list: list[HardwareSelection] = Field(default_factory=list, alias="hardwareList")


class ProjectMembershipBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId", min_length=1)


class HardwareActionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId", min_length=1)
    hardware_id: str = Field(alias="hardwareId", min_length=1)
    quantity: int = Field(gt=0, le=1000000)
    request_id: str = Field(alias="requestId", pattern=REQUEST_ID_PATTERN)


@app.exception_handler(StarletteHTTPException)
async def http_error_response(request: Request, error: StarletteHTTPException):
    return JSONResponse({"error": error.detail}, status_code=error.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_response(request: Request, error: RequestValidationError):
    first = error.errors()[0]
    field = str(first["loc"][-1]) if first.get("loc") else "request"
    return JSONResponse({"error": f"{field}: {first['msg']}"}, status_code=422)


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
        grpc.StatusCode.UNIMPLEMENTED: 503,
        grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    }
    status = mapping.get(error.code(), 502)
    raise HTTPException(status_code=status, detail=error.details() or error.code().name)


def _current_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Please log in")
    return user


def _user_json(user):
    return {
        "userId": user.user_id,
        "username": user.username,
        "orgId": user.org_id,
    }


def _operation_result(result):
    if not result.success:
        raise HTTPException(status_code=409, detail=result.error_message or "Request failed")
    return {"success": True}


def _is_member(project, user):
    return project.creator_id == user["userId"] or user["userId"] in project.joined_users


async def _fetch_project(request: Request, project_id: str, org_id: str):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    result = await stub.GetProject(
        projects_pb2.GetProjectRequest(project_id=project_id, org_id=org_id),
        timeout=30,
    )
    return result.project_info


async def _require_member(request: Request, project_id: str, user: dict):
    try:
        project = await _fetch_project(request, project_id, user["orgId"])
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    if not _is_member(project, user):
        raise HTTPException(status_code=403, detail="You are not a member of this project")
    return project


async def _holdings(request: Request, project_id: str):
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    try:
        result = await stub.GetHoldings(
            hardware_pb2.GetHoldingsRequest(project_id=project_id),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        logger.warning("Could not load holdings for %s: %s", project_id, error.details())
        return {}
    return {item.hardware_id: item.quantity for item in result.holdings}


async def _hardware_names(request: Request):
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    try:
        result = await stub.ListHardware(
            hardware_pb2.ListHardwareRequest(page=1, size=100),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        logger.warning("Could not load hardware names: %s", error.details())
        return {}
    return {item.id: item.name for item in result.items}


@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.post("/auth/signup", status_code=201)
async def signup(body: SignUpBody, request: Request):
    stub = users_pb2_grpc.UsersServiceStub(_channel(request))
    try:
        result = await stub.SignUp(
            users_pb2.SignUpRequest(
                username=body.username,
                password=body.password,
                org_id=body.agency_code,
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"user": _user_json(result.user)}


@app.post("/auth/login")
async def login(body: LoginBody, request: Request):
    stub = users_pb2_grpc.UsersServiceStub(_channel(request))
    try:
        result = await stub.Login(
            users_pb2.LoginRequest(username=body.username, password=body.password),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    user = _user_json(result.user)
    request.session.clear()
    request.session["user"] = user
    return {"data": user["username"], "user": user}


@app.post("/auth/logout", status_code=204)
async def logout(request: Request):
    request.session.clear()
    return Response(status_code=204)


@app.get("/auth/me")
async def me(user: dict = Depends(_current_user)):
    return {"user": user}


@app.post("/projects")
async def create_project(
    body: CreateProjectBody,
    request: Request,
    user: dict = Depends(_current_user),
):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    payload = projects_pb2.CreateProjectRequest(
        creator_id=user["userId"],
        project_id=body.project_id,
        project_name=body.project_name,
        org_id=user["orgId"],
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
    return _operation_result(result)


@app.post("/projects/join")
async def join_project(
    body: ProjectMembershipBody,
    request: Request,
    user: dict = Depends(_current_user),
):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    try:
        result = await stub.JoinProject(
            projects_pb2.ProjectMembershipRequest(
                project_id=body.project_id,
                org_id=user["orgId"],
                user_id=user["userId"],
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return _operation_result(result)


@app.post("/projects/leave")
async def leave_project(
    body: ProjectMembershipBody,
    request: Request,
    user: dict = Depends(_current_user),
):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    try:
        result = await stub.LeaveProject(
            projects_pb2.ProjectMembershipRequest(
                project_id=body.project_id,
                org_id=user["orgId"],
                user_id=user["userId"],
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return _operation_result(result)


@app.get("/projects")
async def list_projects(
    request: Request,
    projectId: str | None = None,
    user: dict = Depends(_current_user),
):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    args = {"org_id": user["orgId"]}
    if projectId is not None:
        args["project_id"] = projectId
    try:
        result = await stub.SearchProjects(projects_pb2.SearchProjectsRequest(**args), timeout=30)
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"projectList": [
        {"projectId": p.project_id, "projectName": p.project_name, "orgId": p.org_id}
        for p in result.project_list
    ]}


@app.get("/projects/mine")
async def list_my_projects(request: Request, user: dict = Depends(_current_user)):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    try:
        result = await stub.SearchProjects(
            projects_pb2.SearchProjectsRequest(org_id=user["orgId"]),
            timeout=30,
        )
        projects = await asyncio.gather(*[
            _fetch_project(request, summary.project_id, user["orgId"])
            for summary in result.project_list
        ])
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)

    mine = [project for project in projects if _is_member(project, user)]
    if not mine:
        return {"projects": []}

    names, *holdings = await asyncio.gather(
        _hardware_names(request),
        *[_holdings(request, project.project_id) for project in mine],
    )
    return {"projects": [
        {
            "projectId": project.project_id,
            "projectName": project.project_name,
            "projectDesc": project.project_desc,
            "hardware": {
                names.get(hardware_id, hardware_id): quantity
                for hardware_id, quantity in held.items()
            },
        }
        for project, held in zip(mine, holdings)
    ]}


@app.get("/projects/{project_id}")
async def get_project(
    request: Request,
    project_id: str,
    user: dict = Depends(_current_user),
):
    p = await _require_member(request, project_id, user)
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
        "holdings": await _holdings(request, p.project_id),
    }}


@app.get("/hardware")
async def list_hardware(
    request: Request,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    category: str = "",
    status: str = "",
    user: dict = Depends(_current_user),
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


@app.post("/hardware/check-out")
async def check_out(
    body: HardwareActionBody,
    request: Request,
    user: dict = Depends(_current_user),
):
    await _require_member(request, body.project_id, user)
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    try:
        await stub.CheckOut(
            hardware_pb2.CheckOutRequest(
                hardware_id=body.hardware_id,
                project_id=body.project_id,
                user_id=user["userId"],
                quantity=body.quantity,
                request_id=body.request_id,
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"success": True}


@app.post("/hardware/check-in")
async def check_in(
    body: HardwareActionBody,
    request: Request,
    user: dict = Depends(_current_user),
):
    await _require_member(request, body.project_id, user)
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    try:
        await stub.CheckIn(
            hardware_pb2.CheckInRequest(
                hardware_id=body.hardware_id,
                project_id=body.project_id,
                user_id=user["userId"],
                quantity=body.quantity,
                request_id=body.request_id,
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"success": True}
