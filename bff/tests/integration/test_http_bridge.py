import grpc
import httpx
import pytest

from app.http_api import app
from app.modules.projects.grpc_service import ProjectsService
from app.modules.hardware.grpc_service import HardwareService
from proto import projects_pb2_grpc, hardware_pb2_grpc


class FakeProjects:
    async def search_projects(self, filters):
        return {"projectList": [{"projectId": "P001", "projectName": "Test", "orgId": "ORG001"}]}


class FakeHardware:
    async def list_hardware(self, page=1, size=20, category="", status=""):
        return {"items": [{"_id": "hw1", "name": "Monitor", "category": "Monitor",
                          "asset_tag": "MON-1", "status": "active", "total": 2,
                          "out": 0, "reserved": 0, "version": 1, "available": 2}],
                "total": 1, "page": page, "size": size}


@pytest.mark.asyncio
async def test_http_bridge_to_grpc():
    server = grpc.aio.server()
    projects_pb2_grpc.add_ProjectsServiceServicer_to_server(ProjectsService(FakeProjects()), server)
    hardware_pb2_grpc.add_HardwareServiceServicer_to_server(HardwareService(FakeHardware()), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    app.state.grpc_channel = channel
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            p = await client.get("/projects")
            assert p.status_code == 200
            assert p.json()["projectList"][0]["orgId"] == "ORG001"
            h = await client.get("/hardware")
            assert h.status_code == 200
            assert h.json()["items"][0]["available"] == 2
            invalid = await client.get("/hardware?size=101")
            assert invalid.status_code == 422
    finally:
        await channel.close()
        await server.stop(grace=0)
        app.state.grpc_channel = None
