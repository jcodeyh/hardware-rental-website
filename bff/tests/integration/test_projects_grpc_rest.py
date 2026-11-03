
import grpc
import httpx
import pytest

from app.modules.projects.grpc_service import ProjectsService
from app.modules.projects.rest_client import ProjectsRestClient
from proto import projects_pb2 as pb
from proto import projects_pb2_grpc as pb_grpc


@pytest.mark.asyncio
async def test_grpc_to_rest_full_flow():
    requests_seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)

        if (
            request.method == "POST"
            and request.url.path == "/projects/search_project"
        ):
            assert request.headers["content-type"] == "application/json"

            return httpx.Response(
                200,
                json={
                    "projectList": [
                        {
                            "projectId": "P001",
                            "projectName": "Office Equipment",
                            "orgId": "ORG001",
                        }
                    ]
                },
            )

        if (
            request.method == "GET"
            and request.url.path == "/projects/P001"
        ):
            assert request.url.params["orgId"] == "ORG001"

            return httpx.Response(
                200,
                json={
                    "projectInfo": {
                        "projectId": "P001",
                        "projectName": "Office Equipment",
                        "projectDesc": "Purchase office hardware",
                        "creatorId": "user1",
                        "orgId": "ORG001",
                        "budget": 50000,
                        "hardwareList": [
                            {
                                "hardwareId": "HW001",
                                "capacity": 20,
                            }
                        ],
                        "joined_users": ["user2"],
                    }
                },
            )

        return httpx.Response(
            404,
            json={"detail": "Project not found"},
        )

    rest_client = ProjectsRestClient(
        "https://projects.example.test"
    )

    await rest_client.client.aclose()

    rest_client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://projects.example.test",
    )

    server = grpc.aio.server()

    pb_grpc.add_ProjectsServiceServicer_to_server(
        ProjectsService(rest_client),
        server,
    )

    port = server.add_insecure_port("127.0.0.1:0")
    assert port > 0

    await server.start()

    try:
        async with grpc.aio.insecure_channel(
            f"127.0.0.1:{port}"
        ) as channel:
            stub = pb_grpc.ProjectsServiceStub(channel)

            search = await stub.SearchProjects(
                pb.SearchProjectsRequest()
            )

            assert len(search.project_list) == 1
            assert search.project_list[0].project_id == "P001"
            assert search.project_list[0].project_name == "Office Equipment"
            assert search.project_list[0].org_id == "ORG001"

            detail = await stub.GetProject(
                pb.GetProjectRequest(
                    project_id="P001",
                    org_id="ORG001",
                )
            )

            assert detail.project_info.project_id == "P001"
            assert detail.project_info.project_name == "Office Equipment"
            assert detail.project_info.creator_id == "user1"
            assert detail.project_info.org_id == "ORG001"
            assert detail.project_info.budget == 50000
            assert detail.project_info.hardware_list[0].hardware_id == "HW001"
            assert detail.project_info.hardware_list[0].capacity == 20
            assert "user2" in detail.project_info.joined_users

            with pytest.raises(grpc.aio.AioRpcError) as error:
                await stub.GetProject(
                    pb.GetProjectRequest(
                        project_id="UNKNOWN",
                        org_id="ORG001",
                    )
                )

            assert error.value.code() == grpc.StatusCode.NOT_FOUND

        assert len(requests_seen) == 3
        assert requests_seen[0].method == "POST"
        assert requests_seen[0].url.path == "/projects/search_project"
        assert requests_seen[1].method == "GET"
        assert requests_seen[1].url.path == "/projects/P001"
        assert requests_seen[1].url.params["orgId"] == "ORG001"
        assert requests_seen[2].method == "GET"
        assert requests_seen[2].url.path == "/projects/UNKNOWN"
        assert requests_seen[2].url.params["orgId"] == "ORG001"

    finally:
        await server.stop(grace=0)
        await rest_client.close()
