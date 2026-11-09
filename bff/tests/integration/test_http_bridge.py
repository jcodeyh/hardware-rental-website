import grpc
import httpx
import pytest
import pytest_asyncio

from app import http_api
from app.http_api import app
from app.modules.hardware.grpc_client import HardwareGrpcClient
from app.modules.hardware.grpc_service import HardwareService
from app.modules.projects.grpc_service import ProjectsService
from app.modules.users.grpc_service import LocalUsers, UsersService
from app.modules.users.rest_client import UsersRestClient
from app.modules.users.store import LocalUserStore
from proto import hardware_pb2_grpc, projects_pb2_grpc, users_pb2_grpc
from tests.fakes.hardware_upstream import CODE, TEAM, start_fake_hardware
from tests.fakes.users_api import VALID_CODE, FakeUsersApi


class FakeProjects:
    def __init__(self):
        self.created = []
        self.joined = []
        self.searches = []
        self.budget_requests = []
        self.budget_response = None
        self.projects = {
            "P_OWN": {
                "projectId": "P_OWN", "projectName": "Mine", "orgId": "AUS",
                "creatorId": "u_maria", "joined_users": ["u_maria"], "budget": 10,
                "hardwareList": [{"hardwareId": "hw1", "capacity": 5}],
            },
            "P_OTHER": {
                "projectId": "P_OTHER", "projectName": "Theirs", "orgId": "AUS",
                "creatorId": "u_other", "joined_users": ["u_other"], "budget": 10,
            },
        }

    async def search_projects(self, filters):
        self.searches.append(filters)
        return {"projectList": [
            {"projectId": p["projectId"], "projectName": p["projectName"], "orgId": p["orgId"]}
            for p in self.projects.values()
        ]}

    async def get_project(self, project_id, org_id):
        return {"projectInfo": self.projects[project_id]}

    async def create_project(self, data):
        self.created.append(data)
        return {"success": True, "errorMessage": ""}

    async def join_project(self, data):
        self.joined.append(data)
        return {"success": True, "errorMessage": ""}

    async def get_budget_context(self, data):
        self.budget_requests.append(data)
        if self.budget_response is not None:
            raise self.budget_response
        return {
            "success": True, "orgId": data["orgId"], "budget": data["budget"],
            "items": [{
                "description": "LIGHTS, EMERGENCY", "quantity": 20,
                "matchedCategory": "LIGHTS, EMERGENCY", "confidence": 1.0,
                "unitPrice": {"median": 145.0, "low": 98.5, "high": 210.0, "purchases": 42},
                "estimatedCost": {"low": 1970.0, "typical": 2900.0, "high": 4200.0},
            }, {
                "description": "unicorn", "quantity": 1,
                "unitPrice": "not available", "estimatedCost": "not available",
            }],
            "totalEstimate": {"low": 1970.0, "typical": 2900.0, "high": 4200.0},
            "unpricedItems": 1,
            "withinBudget": None,
        }


async def _start_bff(tmp_path, users_backend):
    upstream, upstream_server, target = await start_fake_hardware()
    upstream.add_hardware("hw1", "Monitor", "Monitor", 10)
    upstream.add_hardware("hw2", "ThinkPad", "Laptop", 4)
    hardware_client = HardwareGrpcClient(target, TEAM, CODE, timeout=5, use_tls=False)
    server = grpc.aio.server()
    channel = None

    async def close():
        if channel is not None:
            await channel.close()
        await server.stop(grace=0)
        await hardware_client.close()
        await upstream_server.stop(grace=0)
        app.state.grpc_channel = None

    try:
        projects = await _wire(server, upstream, hardware_client, tmp_path, users_backend)
        channel = app.state.grpc_channel
    except BaseException:
        await close()
        raise
    return projects, upstream, close


async def _wire(server, upstream, hardware_client, tmp_path, users_backend):
    await hardware_client.allocate("hw1", "AUS:P_OWN", 5, "seed", "seed-1")
    projects = FakeProjects()
    projects_pb2_grpc.add_ProjectsServiceServicer_to_server(ProjectsService(projects), server)
    hardware_pb2_grpc.add_HardwareServiceServicer_to_server(HardwareService(hardware_client), server)
    if users_backend is None:
        users_backend = LocalUsers(LocalUserStore(str(tmp_path / "users.sqlite3")))
    users_pb2_grpc.add_UsersServiceServicer_to_server(UsersService(users_backend), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    app.state.grpc_channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    return projects


@pytest_asyncio.fixture
async def bff(tmp_path):
    projects, upstream, close = await _start_bff(tmp_path, None)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, projects, upstream
    await close()


@pytest_asyncio.fixture
async def team_bff(tmp_path):
    users_api = FakeUsersApi()
    users_client = UsersRestClient(
        "https://users.example.test", transport=httpx.MockTransport(users_api.handler)
    )
    projects, upstream, close = await _start_bff(tmp_path, users_client)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, users_api
    await close()
    await users_client.close()


async def _log_in(client, username="maria"):
    signup = await client.post(
        "/auth/signup",
        json={"username": username, "password": "correct-horse", "agencyCode": "AUS"},
    )
    assert signup.status_code == 201
    login = await client.post("/auth/login", json={"username": username, "password": "correct-horse"})
    assert login.status_code == 200
    assert login.json()["nextStep"] is None
    assert login.json()["user"]["userId"] == f"u_{username}"


def _calls(upstream, name):
    return [request for call, request in upstream.state.calls if call == name]


@pytest.mark.asyncio
async def test_requires_login(bff):
    client, _, _ = bff
    for route in ("/projects", "/projects/mine", "/hardware", "/auth/me", "/dashboard/my-hardware"):
        response = await client.get(route)
        assert response.status_code == 401
        assert response.json()["error"] == "Please log in"
    budget = await client.post("/budget-context", json={"budget": 1, "items": [{"description": "x", "quantity": 1}]})
    assert budget.status_code == 401


@pytest.mark.asyncio
async def test_local_login_rejects_wrong_password_and_duplicate_signup(bff):
    client, _, _ = bff
    await _log_in(client)
    wrong = await client.post("/auth/login", json={"username": "maria", "password": "wrong"})
    assert wrong.status_code == 401
    assert wrong.json()["error"] == "Invalid username or password"
    duplicate = await client.post(
        "/auth/signup",
        json={"username": "MARIA", "password": "another-pass", "agencyCode": "DAL"},
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_signup_validates_user_team_rules(bff):
    client, _, _ = bff
    for body in (
        {"username": ".maria", "password": "correct-horse", "agencyCode": "AUS"},
        {"username": "maria", "password": "short", "agencyCode": "AUS"},
        {"username": "maria", "password": "x" * 73, "agencyCode": "AUS"},
        {"username": "maria", "password": "correct-horse", "agencyCode": "NYC"},
    ):
        assert (await client.post("/auth/signup", json=body)).status_code == 422


@pytest.mark.asyncio
async def test_logout_ends_session(bff):
    client, _, _ = bff
    await _log_in(client)
    assert (await client.get("/auth/me")).status_code == 200
    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_team_login_enrolls_then_verifies_two_factor(team_bff):
    client, users_api = team_bff
    signup = await client.post(
        "/auth/signup",
        json={"username": "maria", "password": "correct-horse", "agencyCode": "AUS"},
        headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"},
    )
    assert signup.status_code == 201
    assert signup.json()["user"] == {"userId": "1", "username": "maria", "orgId": "AUS"}
    assert users_api.requests[-1].headers["x-forwarded-for"] == "203.0.113.9"

    login = await client.post("/auth/login", json={"username": "maria", "password": "correct-horse"})
    assert login.json() == {"user": None, "nextStep": "2fa_setup"}
    assert (await client.get("/auth/me")).status_code == 401

    setup = await client.post("/auth/2fa/setup")
    assert setup.status_code == 200
    assert setup.json()["qrCodeDataUrl"].startswith("data:image/png")
    assert users_api.requests[-1].headers["authorization"] == "Bearer mfa.maria"

    wrong = await client.post("/auth/2fa/verify", json={"code": "000000"})
    assert wrong.status_code == 401
    assert wrong.json()["error"] == "Invalid two-factor code."

    enabled = await client.post("/auth/2fa/verify", json={"code": VALID_CODE})
    assert enabled.status_code == 200
    assert users_api.requests[-1].url.path == "/users/2fa/enable"
    assert (await client.get("/auth/me")).json()["user"]["userId"] == "1"

    await client.post("/auth/logout")
    again = await client.post("/auth/login", json={"username": "maria", "password": "correct-horse"})
    assert again.json()["nextStep"] == "2fa_verify"
    assert (await client.post("/auth/2fa/setup")).status_code == 409
    verified = await client.post("/auth/2fa/verify", json={"code": VALID_CODE})
    assert verified.status_code == 200
    assert users_api.requests[-1].url.path == "/users/2fa/verify"


@pytest.mark.asyncio
async def test_team_login_errors(team_bff, monkeypatch):
    client, _ = team_bff
    assert (await client.post("/auth/2fa/verify", json={"code": VALID_CODE})).status_code == 409
    assert (await client.post("/auth/2fa/verify", json={"code": "12ab56"})).status_code == 422
    bad = await client.post("/auth/login", json={"username": "ghost", "password": "whatever"})
    assert bad.status_code == 401
    assert bad.json()["error"] == "Invalid username or password."
    short = await client.post(
        "/auth/signup", json={"username": "maria", "password": "correct-horse", "agencyCode": "AUS"}
    )
    assert short.status_code == 201

    await client.post("/auth/login", json={"username": "maria", "password": "correct-horse"})
    real_time = http_api.time.time
    monkeypatch.setattr(http_api.time, "time", lambda: real_time() + http_api.PENDING_LOGIN_SECONDS + 1)
    expired = await client.post("/auth/2fa/setup")
    assert expired.status_code == 401
    assert expired.json()["error"] == "Your sign-in expired. Log in again."


@pytest.mark.asyncio
async def test_identity_comes_from_session_not_body(bff):
    client, projects, _ = bff
    await _log_in(client)
    created = await client.post("/projects", json={
        "projectId": "P_NEW", "projectName": "New", "budget": 5,
        "creatorId": "u_forged", "orgId": "DAL",
    })
    assert created.status_code == 200
    assert projects.created[0]["creatorId"] == "u_maria"
    assert projects.created[0]["orgId"] == "AUS"
    joined = await client.post("/projects/join", json={
        "projectId": "P_OTHER", "userId": "u_forged", "orgId": "DAL",
    })
    assert joined.status_code == 200
    assert projects.joined[0]["userId"] == "u_maria"
    assert projects.joined[0]["orgId"] == "AUS"


@pytest.mark.asyncio
async def test_create_project_sends_allocation_and_reserves_hardware(bff):
    client, projects, upstream = bff
    await _log_in(client)
    body = {
        "projectId": "P_NEW", "projectName": "New", "budget": 5,
        "hardwareList": [{"hardwareId": "hw2", "allocation": 3}, {"hardwareId": "hw1", "capacity": 2}],
    }
    created = await client.post("/projects", json=body)
    assert created.json() == {"success": True, "warnings": []}
    assert projects.created[0]["hardwareList"] == [
        {"hardwareId": "hw2", "allocation": 3, "capacity": 3},
        {"hardwareId": "hw1", "allocation": 2, "capacity": 2},
    ]
    allocations = upstream.state.allocations
    assert allocations["hw2:AUS:P_NEW"].quantity == 3
    assert allocations["hw1:AUS:P_NEW"].quantity == 2
    assert all(r.reason for r in _calls(upstream, "AllocateHardware"))

    retried = await client.post("/projects", json=body)
    assert retried.json()["warnings"] == []
    assert upstream.state.hardware["hw2"].reserved == 3


@pytest.mark.asyncio
async def test_create_project_reports_hardware_it_could_not_reserve(bff):
    client, _, _ = bff
    await _log_in(client)
    created = await client.post("/projects", json={
        "projectId": "P_BIG", "projectName": "Big", "budget": 5,
        "hardwareList": [{"hardwareId": "hw2", "allocation": 99}, {"hardwareId": "nope", "allocation": 1}],
    })
    assert created.status_code == 200
    warnings = created.json()["warnings"]
    assert len(warnings) == 2
    assert "not enough unallocated stock" in warnings[0]
    assert "unknown hardware id" in warnings[1]


@pytest.mark.asyncio
async def test_project_detail_merges_plan_with_hardware_service(bff):
    client, _, _ = bff
    await _log_in(client)
    await client.post("/hardware/check-out", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 2, "requestId": "req-1",
    })
    detail = (await client.get("/projects/P_OWN")).json()["projectInfo"]
    assert detail["hardwareAvailable"] is True
    assert detail["hardwareList"] == [{
        "hardwareId": "hw1", "name": "Monitor", "allocation": 5,
        "reserved": 5, "out": 2, "remaining": 3,
    }]
    assert "holdings" not in detail


@pytest.mark.asyncio
async def test_project_detail_survives_hardware_outage(bff):
    client, _, upstream = bff
    await _log_in(client)
    upstream.state.fail_next["ListAllocations"] = (grpc.StatusCode.UNAVAILABLE, "restarting")
    assert (await client.get("/projects/P_OWN")).json()["projectInfo"]["hardwareList"][0]["reserved"] == 5
    upstream.state.fail_next["ListAllocations"] = (grpc.StatusCode.PERMISSION_DENIED, "not allowed")
    detail = (await client.get("/projects/P_OWN")).json()["projectInfo"]
    assert detail["hardwareAvailable"] is False
    assert detail["hardwareList"][0] == {
        "hardwareId": "hw1", "name": "hw1", "allocation": 5, "reserved": 0, "out": 0, "remaining": 0,
    }


@pytest.mark.asyncio
async def test_my_projects_filters_by_membership_and_names_hardware(bff):
    client, projects, _ = bff
    await _log_in(client)
    await client.post("/hardware/check-out", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 4, "requestId": "req-1",
    })
    response = await client.get("/projects/mine")
    assert projects.searches[-1] == {"orgId": "AUS"}
    mine = response.json()["projects"]
    assert [p["projectId"] for p in mine] == ["P_OWN"]
    assert mine[0]["hardware"] == {"Monitor": 4}


@pytest.mark.asyncio
async def test_hardware_list(bff):
    client, _, _ = bff
    await _log_in(client)
    response = await client.get("/hardware?size=2")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [i["name"] for i in items] == ["Monitor", "ThinkPad"]
    assert items[0]["reserved"] == 5
    assert items[0]["available"] == 10
    assert (await client.get("/hardware?size=101")).status_code == 422


@pytest.mark.asyncio
async def test_check_out_uses_session_user_scoped_project_and_request_id(bff):
    client, _, upstream = bff
    await _log_in(client)
    response = await client.post("/hardware/check-out", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 2, "requestId": "req-1",
    })
    assert response.status_code == 200
    checkout = _calls(upstream, "CreateCheckout")[0]
    assert (checkout.user_id, checkout.project_id, checkout.request_id) == ("u_maria", "AUS:P_OWN", "req-1")
    assert checkout.quantity == 2 and checkout.reason

    too_many = await client.post("/hardware/check-out", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 4, "requestId": "req-2",
    })
    assert too_many.status_code == 409
    assert too_many.json()["error"] == "not enough reserved stock"


@pytest.mark.asyncio
async def test_hardware_actions_require_membership(bff):
    client, _, upstream = bff
    await _log_in(client)
    for route in ("/hardware/check-out", "/hardware/check-in"):
        response = await client.post(route, json={
            "projectId": "P_OTHER", "hardwareId": "hw1", "quantity": 1, "requestId": "req-2",
        })
        assert response.status_code == 403
    assert _calls(upstream, "CreateCheckout") == []
    assert _calls(upstream, "ReturnCheckout") == []


@pytest.mark.asyncio
async def test_check_in_spans_checkouts_across_pages(bff):
    client, _, upstream = bff
    await _log_in(client)
    for n in range(3):
        await client.post("/hardware/check-out", json={
            "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 1, "requestId": f"out-{n}",
        })
    response = await client.post("/hardware/check-in", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 3, "requestId": "req-3",
    })
    assert response.status_code == 200
    returns = _calls(upstream, "ReturnCheckout")
    assert [(r.checkout_id, r.quantity, r.request_id) for r in returns] == [
        ("co1", 1, "req-3.co1"), ("co2", 1, "req-3.co2"), ("co3", 1, "req-3.co3"),
    ]
    assert upstream.state.hardware["hw1"].out == 0


@pytest.mark.asyncio
async def test_check_in_rejects_more_than_held(bff):
    client, _, upstream = bff
    await _log_in(client)
    await client.post("/hardware/check-out", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 4, "requestId": "req-1",
    })
    response = await client.post("/hardware/check-in", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 5, "requestId": "req-4",
    })
    assert response.status_code == 409
    assert response.json()["error"] == "This project only holds 4 of that hardware"
    assert _calls(upstream, "ReturnCheckout") == []


@pytest.mark.asyncio
async def test_my_hardware_lists_categories_including_returned(bff):
    client, _, upstream = bff
    await _log_in(client)
    assert (await client.get("/dashboard/my-hardware")).json() == {"categories": [], "items": []}
    await client.post("/projects", json={
        "projectId": "P_OWN2", "projectName": "Two", "budget": 1,
        "hardwareList": [{"hardwareId": "hw2", "allocation": 2}],
    })
    upstream.state.allocations["hw2:AUS:P_OWN"] = upstream.state.allocations.pop("hw2:AUS:P_OWN2")
    upstream.state.allocations["hw2:AUS:P_OWN"].project_id = "AUS:P_OWN"
    for hardware_id, request_id in (("hw1", "a"), ("hw1", "b"), ("hw2", "c")):
        await client.post("/hardware/check-out", json={
            "projectId": "P_OWN", "hardwareId": hardware_id, "quantity": 1, "requestId": request_id,
        })
    await client.post("/hardware/check-in", json={
        "projectId": "P_OWN", "hardwareId": "hw2", "quantity": 1, "requestId": "d",
    })
    body = (await client.get("/dashboard/my-hardware")).json()
    assert body["categories"] == ["Laptop", "Monitor"]
    by_id = {item["hardwareId"]: item for item in body["items"]}
    assert by_id["hw1"] == {"hardwareId": "hw1", "name": "Monitor", "category": "Monitor",
                            "quantity": 2, "outstanding": 2}
    assert by_id["hw2"]["outstanding"] == 0
    assert _calls(upstream, "ListCheckouts")[-1].user_id == "u_maria"
    assert _calls(upstream, "ListCheckouts")[-1].outstanding is False


@pytest.mark.asyncio
async def test_budget_context_uses_session_org_and_passes_answer_through(bff):
    client, projects, _ = bff
    await _log_in(client)
    response = await client.post("/budget-context", json={
        "budget": 20000, "orgId": "DAL",
        "items": [{"description": "LIGHTS, EMERGENCY", "quantity": 20}, {"description": "unicorn", "quantity": 1}],
    })
    assert response.status_code == 200
    assert projects.budget_requests[0] == {
        "orgId": "AUS", "budget": 20000.0,
        "items": [{"description": "LIGHTS, EMERGENCY", "quantity": 20}, {"description": "unicorn", "quantity": 1}],
    }
    body = response.json()
    assert body["withinBudget"] is None
    assert body["unpricedItems"] == 1
    assert body["items"][1]["estimatedCost"] == "not available"
    assert body["totalEstimate"]["typical"] == 2900.0

    assert (await client.post("/budget-context", json={"budget": 1, "items": []})).status_code == 422
    assert (await client.post("/budget-context", json={
        "budget": 1, "items": [{"description": "x", "quantity": 0}],
    })).status_code == 422


@pytest.mark.asyncio
async def test_budget_context_upstream_error_message(bff):
    client, projects, _ = bff
    await _log_in(client)
    request = httpx.Request("POST", "https://projects.example.test/get_budget_context")
    projects.budget_response = httpx.HTTPStatusError(
        "boom", request=request,
        response=httpx.Response(500, json={"success": False, "message": "Budget data is unavailable right now"}, request=request),
    )
    response = await client.post("/budget-context", json={
        "budget": 1, "items": [{"description": "x", "quantity": 1}],
    })
    assert response.status_code == 502
    assert response.json()["error"] == "Budget data is unavailable right now"


@pytest.mark.asyncio
async def test_wrong_hardware_team_code_is_not_a_user_login_error(tmp_path):
    upstream, upstream_server, target = await start_fake_hardware()
    client = HardwareGrpcClient(target, TEAM, "wrong-code", timeout=5, use_tls=False)
    server = grpc.aio.server()
    hardware_pb2_grpc.add_HardwareServiceServicer_to_server(HardwareService(client), server)
    users_pb2_grpc.add_UsersServiceServicer_to_server(
        UsersService(LocalUsers(LocalUserStore(str(tmp_path / "u.sqlite3")))), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    app.state.grpc_channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as http:
            await _log_in(http)
            response = await http.get("/hardware")
            assert response.status_code == 502
            assert response.json()["error"] == "The Hardware service rejected our team credentials"
    finally:
        await app.state.grpc_channel.close()
        app.state.grpc_channel = None
        await server.stop(grace=0)
        await client.close()
        await upstream_server.stop(grace=0)
