
import httpx


class HardwareRestClient:
    def __init__(
        self,
        base_url: str,
        session_cookie: str = "",
        timeout: float = 15.0,
        transport=None,
    ):
        if not base_url:
            raise ValueError("Hardware API URL is required")

        cookies = (
            {"__Host-hardware": session_cookie}
            if session_cookie else None
        )

        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout,
            transport=transport,
            cookies=cookies,
        )

    async def list_hardware(
        self,
        page: int = 1,
        size: int = 20,
        category: str = "",
        status: str = "",
    ) -> dict:
        params = {
            "page": page,
            "size": size,
        }

        if category:
            params["category"] = category

        if status:
            params["status"] = status

        response = await self.client.get(
            "api/hardware",
            params=params,
        )

        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()
