import asyncio
import hashlib
import logging
import secrets
import time
from typing import Literal

import grpc
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from google.protobuf import json_format
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
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
PENDING_LOGIN_SECONDS = 5 * 60

settings = get_settings()

app = FastAPI(title="Hardware Rental BFF", version="0.4.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret or secrets.token_urlsafe(32),
    session_cookie="haas_session",
    max_age=SESSION_MAX_AGE_SECONDS,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)


class SignUpBody(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,49}$")
    password: str = Field(min_length=8, max_length=72)
    agency_code: Literal["AUS", "DAL", "TEX"] = Field(alias="agencyCode")


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class TwoFactorCodeBody(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


class HardwareSelection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hardware_id: str = Field(alias="hardwareId", min_length=1)
    allocation: int = Field(
        gt=0, le=1000000, validation_alias=AliasChoices("allocation", "capacity")
    )


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


class BudgetItemBody(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0, le=1000000)


class BudgetContextBody(BaseModel):
    budget: float = Field(ge=0, le=1e12)
    items: list[BudgetItemBody] = Field(min_length=1, max_length=20)


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
        grpc.StatusCode.ABORTED: 409,
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


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    if first:
        return first
    return request.client.host if request.client else ""


def _user_json(user):
    return {
        "userId": user.user_id,
        "username": user.username,
        "orgId": user.org_id,
    }


def _start_session(request: Request, user) -> dict:
    data = _user_json(user)
    request.session.clear()
    request.session["user"] = data
    return data


def _pending_login(request: Request) -> dict:
    pending = request.session.get("pending")
    if not pending:
        raise HTTPException(status_code=409, detail="Start by logging in with your username and password")
    if time.time() - pending["at"] > PENDING_LOGIN_SECONDS:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Your sign-in expired. Log in again.")
    return pending


def _operation_result(result):
    if not result.success:
        raise HTTPException(status_code=409, detail=result.error_message or "Request failed")
    return {"success": True}


def _is_member(project, user):
    return project.creator_id == user["userId"] or user["userId"] in project.joined_users


def _hardware_project_id(user: dict, project_id: str) -> str:
    if settings.hardware_project_id_org_prefix:
        return f"{user['orgId']}:{project_id}"
    return project_id


def _stable_request_id(*parts) -> str:
    digest = hashlib.sha256(":".join(str(p) for p in parts).encode()).hexdigest()
    return f"bff-{digest[:40]}"


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


async def _project_hardware(request: Request, user: dict, project_id: str):
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    try:
        result = await stub.GetProjectHardware(
            hardware_pb2.GetProjectHardwareRequest(
                project_id=_hardware_project_id(user, project_id)
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        logger.warning("Could not load hardware for %s: %s", project_id, error.details())
        return None
    return {item.hardware_id: item for item in result.items}


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
                client_ip=_client_ip(request),
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
            users_pb2.LoginRequest(
                username=body.username,
                password=body.password,
                client_ip=_client_ip(request),
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    if result.HasField("user"):
        return {"user": _start_session(request, result.user), "nextStep": None}
    request.session.clear()
    request.session["pending"] = {
        "mfa": result.mfa_token,
        "step": result.next_step,
        "at": time.time(),
    }
    return {"user": None, "nextStep": result.next_step}


@app.post("/auth/2fa/setup")
async def two_factor_setup(request: Request):
    pending = _pending_login(request)
    if pending["step"] != "2fa_setup":
        raise HTTPException(status_code=409, detail="Two-factor sign-in is already set up")
    stub = users_pb2_grpc.UsersServiceStub(_channel(request))
    try:
        result = await stub.SetupTwoFactor(
            users_pb2.TwoFactorSetupRequest(
                mfa_token=pending["mfa"], client_ip=_client_ip(request)
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"qrCodeDataUrl": result.qr_code_data_url, "secret": result.secret}


@app.post("/auth/2fa/verify")
async def two_factor_verify(body: TwoFactorCodeBody, request: Request):
    pending = _pending_login(request)
    stub = users_pb2_grpc.UsersServiceStub(_channel(request))
    try:
        result = await stub.CompleteTwoFactor(
            users_pb2.TwoFactorCodeRequest(
                mfa_token=pending["mfa"],
                code=body.code,
                enroll=pending["step"] == "2fa_setup",
                client_ip=_client_ip(request),
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"user": _start_session(request, result.user)}


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
                allocation=item.allocation,
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
    _operation_result(result)
    warnings = await _reserve_hardware(request, user, body)
    return {"success": True, "warnings": warnings}


async def _reserve_hardware(request: Request, user: dict, body: CreateProjectBody):
    if not body.hardware_list:
        return []
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    project_id = _hardware_project_id(user, body.project_id)

    async def reserve(item):
        try:
            await stub.ReserveHardware(
                hardware_pb2.ReserveHardwareRequest(
                    hardware_id=item.hardware_id,
                    project_id=project_id,
                    user_id=user["userId"],
                    quantity=item.allocation,
                    request_id=_stable_request_id(
                        "reserve", project_id, item.hardware_id, item.allocation
                    ),
                ),
                timeout=30,
            )
        except grpc.aio.AioRpcError as error:
            logger.warning("Could not reserve %s for %s: %s", item.hardware_id, project_id, error.details())
            return f"Could not reserve {item.allocation} of {item.hardware_id}: {error.details() or error.code().name}"
        return None

    results = await asyncio.gather(*[reserve(item) for item in body.hardware_list])
    return [warning for warning in results if warning]


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
    hardware = await asyncio.gather(
        *[_project_hardware(request, user, project.project_id) for project in mine]
    )
    return {"projects": [
        {
            "projectId": project.project_id,
            "projectName": project.project_name,
            "projectDesc": project.project_desc,
            "hardware": {
                item.name: item.out for item in (held or {}).values() if item.out > 0
            },
        }
        for project, held in zip(mine, hardware)
    ]}


@app.get("/projects/{project_id}")
async def get_project(
    request: Request,
    project_id: str,
    user: dict = Depends(_current_user),
):
    p = await _require_member(request, project_id, user)
    held = await _project_hardware(request, user, p.project_id)
    planned = {x.hardware_id: x.allocation for x in p.hardware_list}
    hardware_ids = list(dict.fromkeys([*planned, *(held or {})]))
    hardware_list = []
    for hardware_id in hardware_ids:
        item = (held or {}).get(hardware_id)
        reserved = item.reserved if item else 0
        out = item.out if item else 0
        hardware_list.append({
            "hardwareId": hardware_id,
            "name": item.name if item else hardware_id,
            "allocation": planned.get(hardware_id, 0),
            "reserved": reserved,
            "out": out,
            "remaining": max(reserved - out, 0),
        })
    return {"projectInfo": {
        "projectId": p.project_id,
        "projectName": p.project_name,
        "projectDesc": p.project_desc,
        "creatorId": p.creator_id,
        "orgId": p.org_id,
        "budget": p.budget,
        "hardwareList": hardware_list,
        "hardwareAvailable": held is not None,
        "joined_users": list(p.joined_users),
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
                project_id=_hardware_project_id(user, body.project_id),
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
                project_id=_hardware_project_id(user, body.project_id),
                user_id=user["userId"],
                quantity=body.quantity,
                request_id=body.request_id,
            ),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return {"success": True}


@app.get("/dashboard/my-hardware")
async def my_hardware(request: Request, user: dict = Depends(_current_user)):
    stub = hardware_pb2_grpc.HardwareServiceStub(_channel(request))
    try:
        result = await stub.GetUserHardware(
            hardware_pb2.GetUserHardwareRequest(user_id=user["userId"]),
            timeout=30,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    items = [
        {
            "hardwareId": x.hardware_id,
            "name": x.name,
            "category": x.category,
            "quantity": x.quantity,
            "outstanding": x.outstanding,
        }
        for x in result.items
    ]
    categories = sorted({x["category"].strip() for x in items if x["category"].strip()}, key=str.lower)
    return {"categories": categories, "items": items}


@app.post("/budget-context")
async def budget_context(
    body: BudgetContextBody,
    request: Request,
    user: dict = Depends(_current_user),
):
    stub = projects_pb2_grpc.ProjectsServiceStub(_channel(request))
    try:
        result = await stub.GetBudgetContext(
            projects_pb2.BudgetContextRequest(
                org_id=user["orgId"],
                budget=body.budget,
                items=[
                    projects_pb2.BudgetItem(description=i.description, quantity=i.quantity)
                    for i in body.items
                ],
            ),
            timeout=90,
        )
    except grpc.aio.AioRpcError as error:
        _grpc_error(error)
    return json_format.MessageToDict(result)
