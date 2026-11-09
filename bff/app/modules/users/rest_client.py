import httpx


class UsersRestClient:
    def __init__(self, base_url: str, timeout: float = 15.0, transport=None):
        if not base_url.strip():
            raise ValueError("USERS_API_BASE_URL is required")
        if not base_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("Users API must use HTTPS outside localhost")
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    async def _post(self, path, client_ip="", token="", json=None):
        headers = {}
        if client_ip:
            headers["X-Forwarded-For"] = client_ip
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = await self.client.post(path, json=json, headers=headers)
        response.raise_for_status()
        return response.json()

    async def register(self, username, password, org_id, client_ip=""):
        data = await self._post(
            "users/register",
            client_ip,
            json={"agencyCode": org_id, "username": username, "password": password},
        )
        return _user(data["user"])

    async def login(self, username, password, client_ip=""):
        data = await self._post(
            "users/login", client_ip, json={"username": username, "password": password}
        )
        return {"mfa_token": data["mfaToken"], "next_step": data["nextStep"]}

    async def setup_two_factor(self, mfa_token, client_ip=""):
        data = await self._post("users/2fa/setup", client_ip, token=mfa_token)
        return {"qr_code_data_url": data["qrCodeDataUrl"], "secret": data["secret"]}

    async def complete_two_factor(self, mfa_token, code, enroll, client_ip=""):
        path = "users/2fa/enable" if enroll else "users/2fa/verify"
        data = await self._post(path, client_ip, token=mfa_token, json={"code": code})
        return _user(data["user"])

    async def close(self):
        await self.client.aclose()


def _user(data):
    return {
        "user_id": str(data["id"]),
        "username": data["username"],
        "org_id": data["agencyCode"],
    }
