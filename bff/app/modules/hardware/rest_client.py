from urllib.parse import quote

import httpx


class HardwareRestClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 15.0,
        transport=None,
    ):
        if not base_url.strip():
            raise ValueError("HARDWARE_API_BASE_URL is required")
        if not api_key.strip():
            raise ValueError("HARDWARE_API_KEY is required")
        if not base_url.startswith("https://") and not base_url.startswith("http://localhost") and not base_url.startswith("http://127.0.0.1"):
            raise ValueError("Hardware API must use HTTPS outside localhost")

        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            auth=httpx.BasicAuth("front-end", api_key),
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    async def list_hardware(
        self,
        page: int = 1,
        size: int = 20,
        category: str = "",
        status: str = "",
    ) -> dict:
        params = {"page": page, "size": size}
        if category:
            params["category"] = category
        if status:
            params["status"] = status

        response = await self.client.get("api/hardware", params=params)
        response.raise_for_status()
        return response.json()

    async def create_checkout(
        self,
        hardware_id: str,
        project_id: str,
        user_id: str,
        quantity: int,
        reason: str,
        request_id: str,
    ) -> dict:
        response = await self.client.post(
            "api/checkouts",
            json={
                "hardware_id": hardware_id,
                "project_id": project_id,
                "user_id": user_id,
                "quantity": quantity,
                "reason": reason,
                "request_id": request_id,
            },
        )
        response.raise_for_status()
        return response.json()

    async def list_outstanding_checkouts(
        self,
        project_id: str,
        hardware_id: str = "",
    ) -> list[dict]:
        params = {
            "project_id": project_id,
            "outstanding": "true",
            "size": 100,
        }
        if hardware_id:
            params["hardware_id"] = hardware_id

        items = []
        page = 1
        while True:
            response = await self.client.get(
                "api/checkouts",
                params={**params, "page": page},
            )
            response.raise_for_status()
            data = response.json()
            items.extend(data["items"])
            if not data["items"] or len(items) >= data["total"]:
                return items
            page += 1

    async def return_checkout(
        self,
        checkout_id: str,
        quantity: int,
        reason: str,
        request_id: str,
    ) -> dict:
        response = await self.client.post(
            f"api/checkouts/{quote(checkout_id, safe='')}/returns",
            json={
                "quantity": quantity,
                "reason": reason,
                "request_id": request_id,
            },
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()
