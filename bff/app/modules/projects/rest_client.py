
from typing import Any
from urllib.parse import quote

import httpx


class ProjectsRestClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        if not base_url:
            raise ValueError("Projects API base URL is required")

        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout,
            follow_redirects=False,
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict:
        response = await self.client.request(
            method,
            path.lstrip("/"),
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    async def create_project(self, data: dict) -> dict:
        return await self._request(
            "POST", "projects/create_project", json=data
        )

    async def join_project(self, data: dict) -> dict:
        return await self._request(
            "POST", "projects/join_project", json=data
        )

    async def leave_project(self, data: dict) -> dict:
        return await self._request(
            "POST", "projects/leave_project", json=data
        )

    async def search_projects(self, filters: dict) -> dict:
        return await self._request(
            "POST", "projects/search_project", json=filters
        )

    async def get_project(self, project_id: str, org_id: str) -> dict:
        encoded_id = quote(project_id, safe="")

        return await self._request(
            "GET",
            f"projects/{encoded_id}",
            params={"orgId": org_id},
        )
    
    async def close(self) -> None:
        await self.client.aclose()
