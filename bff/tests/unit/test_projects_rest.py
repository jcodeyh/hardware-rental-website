
import httpx
import pytest
import json

from app.modules.projects.rest_client import ProjectsRestClient


@pytest.mark.asyncio

@pytest.mark.asyncio
async def test_search_projects():
    async def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/projects/search_project"

        body = json.loads(request.content)
        assert body["orgId"] == "ORG001"

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

    client = ProjectsRestClient("https://projects.example.test")

    await client.client.aclose()
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://projects.example.test",
    )

    try:
        result = await client.search_projects({
            "orgId": "ORG001"
        })

        assert result["projectList"][0]["projectId"] == "P001"
        assert result["projectList"][0]["orgId"] == "ORG001"

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_project():
    async def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/projects/P001"

        return httpx.Response(
            200,
            json={
                "projectInfo": {
                    "projectId": "P001",
                    "projectName": "Office Equipment",
                    "projectDesc": "",
                    "projectCreatorId": "user1",
                    "budget": 50000,
                    "hardwareList": [],
                    "joined_users": [],
                }
            },
        )

    client = ProjectsRestClient("https://projects.example.test")

    await client.client.aclose()
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://projects.example.test",
    )

    try:
        result = await client.get_project("P001", "ORG001")

        assert result["projectInfo"]["budget"] == 50000
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_projects_not_found():
    async def handler(request):
        return httpx.Response(
            404,
            json={"detail": "Project not found"},
            request=request,
        )

    client = ProjectsRestClient("https://projects.example.test")

    await client.client.aclose()
    client.client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://projects.example.test",
    )

    try:
        with pytest.raises(httpx.HTTPStatusError) as error:
            await client.get_project("P999", "ORG001")

        assert error.value.response.status_code == 404
    finally:
        await client.close()
