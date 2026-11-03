import grpc
import httpx
import pytest
import pytest_asyncio

from app.http_api import app
from app.modules.hardware.grpc_service import HardwareService
from app.modules.projects.grpc_service import ProjectsService
from app.modules.users.grpc_service import UsersService
from app.modules.users.store import LocalUserStore
from proto import hardware_pb2_grpc, projects_pb2_grpc, users_pb2_grpc


class FakeProjects:
    def __init__(self):
        self.created = []
        self.joined = []
        self.searches = []
        self.projects = {
            "P_OWN": {
                "projectId": "P_OWN", "projectName": "Mine", "orgId": "AUS",
                "creatorId": "u_maria", "joined_users": ["u_maria"], "budget": 10,
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
        return {"success": True}

    async def join_project(self, data):
        self.joined.append(data)
        return {"success": True}


class FakeHardware:
    def __init__(self):
        self.created = []
        self.returned = []
        self.outstanding = [
            {"_id": "c1", "hardware_id": "hw1", "quantity": 2, "returned": 1},
            {"_id": "c2", "hardware_id": "hw1", "quantity": 3, "returned": 0},
        ]

    async def list_hardware(self, page=1, size=20, category="", status=""):
        return {"items": [{"_id": "hw1", "name": "Monitor", "category": "Monitor",
                          "asset_tag": "MON-1", "status": "active", "total": 10,
                          "out": 3, "reserved": 2, "version": 1}],
                "total": 1, "page": page, "size": size}

    async def create_checkout(self, **kwargs):
        self.created.append(kwargs)
        return {"_id": "c3"}

    async def list_outstanding_checkouts(self, project_id, hardware_id=""):
        return self.outstanding

    async def return_checkout(self, **kwargs):
        self.returned.append(kwargs)
        return {}


@pytest_asyncio.fixture
async def bff(tmp_path):
    projects = FakeProjects()
    hardware = FakeHardware()
    server = grpc.aio.server()
    projects_pb2_grpc.add_ProjectsServiceServicer_to_server(ProjectsService(projects), server)
    hardware_pb2_grpc.add_HardwareServiceServicer_to_server(HardwareService(hardware), server)
    users_pb2_grpc.add_UsersServiceServicer_to_server(
        UsersService(LocalUserStore(str(tmp_path / "users.sqlite3"))), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    app.state.grpc_channel = channel
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, projects, hardware
    await channel.close()
    await server.stop(grace=0)
    app.state.grpc_channel = None


async def _log_in(client):
    signup = await client.post(
        "/auth/signup",
        json={"username": "maria", "password": "correct-horse", "agencyCode": "AUS"},
    )
    assert signup.status_code == 201
    assert signup.json()["user"]["userId"] == "u_maria"
    login = await client.post(
        "/auth/login",
        json={"username": "maria", "password": "correct-horse"},
    )
    assert login.status_code == 200
    assert login.json()["data"] == "maria"


@pytest.mark.asyncio
async def test_requires_login(bff):
    client, _, _ = bff
    for route in ("/projects", "/projects/mine", "/hardware", "/auth/me"):
        response = await client.get(route)
        assert response.status_code == 401
        assert response.json()["error"] == "Please log in"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password_and_duplicate_signup(bff):
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
async def test_logout_ends_session(bff):
    client, _, _ = bff
    await _log_in(client)
    assert (await client.get("/auth/me")).status_code == 200
    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401


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
async def test_my_projects_filters_by_membership_and_names_holdings(bff):
    client, projects, _ = bff
    await _log_in(client)
    response = await client.get("/projects/mine")
    assert response.status_code == 200
    assert projects.searches[-1] == {"orgId": "AUS"}
    mine = response.json()["projects"]
    assert [p["projectId"] for p in mine] == ["P_OWN"]
    assert mine[0]["hardware"] == {"Monitor": 4}


@pytest.mark.asyncio
async def test_hardware_list_computes_available(bff):
    client, _, _ = bff
    await _log_in(client)
    response = await client.get("/hardware")
    assert response.status_code == 200
    assert response.json()["items"][0]["available"] == 5
    assert (await client.get("/hardware?size=101")).status_code == 422


@pytest.mark.asyncio
async def test_check_out_uses_session_user_and_request_id(bff):
    client, _, hardware = bff
    await _log_in(client)
    response = await client.post("/hardware/check-out", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 2, "requestId": "req-1",
    })
    assert response.status_code == 200
    assert hardware.created[0]["user_id"] == "u_maria"
    assert hardware.created[0]["request_id"] == "req-1"
    assert hardware.created[0]["quantity"] == 2


@pytest.mark.asyncio
async def test_hardware_actions_require_membership(bff):
    client, _, hardware = bff
    await _log_in(client)
    for route in ("/hardware/check-out", "/hardware/check-in"):
        response = await client.post(route, json={
            "projectId": "P_OTHER", "hardwareId": "hw1", "quantity": 1, "requestId": "req-2",
        })
        assert response.status_code == 403
    assert hardware.created == []
    assert hardware.returned == []


@pytest.mark.asyncio
async def test_check_in_spans_multiple_checkouts(bff):
    client, _, hardware = bff
    await _log_in(client)
    response = await client.post("/hardware/check-in", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 3, "requestId": "req-3",
    })
    assert response.status_code == 200
    assert [(r["checkout_id"], r["quantity"]) for r in hardware.returned] == [("c1", 1), ("c2", 2)]
    assert hardware.returned[0]["request_id"] == "req-3.c1"
    assert hardware.returned[1]["request_id"] == "req-3.c2"


@pytest.mark.asyncio
async def test_check_in_rejects_more_than_held(bff):
    client, _, hardware = bff
    await _log_in(client)
    response = await client.post("/hardware/check-in", json={
        "projectId": "P_OWN", "hardwareId": "hw1", "quantity": 5, "requestId": "req-4",
    })
    assert response.status_code == 409
    assert response.json()["error"] == "This project only holds 4 of that hardware"
    assert hardware.returned == []
