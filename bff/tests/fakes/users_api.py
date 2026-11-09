import json

import httpx

VALID_CODE = "123456"


class FakeUsersApi:
    def __init__(self):
        self.users = {}
        self.requests = []
        self.next_id = 1

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = json.loads(request.content) if request.content else {}
        route = (request.method, request.url.path)
        if route == ("POST", "/users/register"):
            return self._register(body)
        if route == ("POST", "/users/login"):
            return self._login(body)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        user = self._user_for_mfa(token)
        if user is None:
            return httpx.Response(401, json={"error": "Missing or invalid authorization token."})
        if route == ("POST", "/users/2fa/setup"):
            user["pending"] = True
            return httpx.Response(200, json={
                "secret": "JBSWY3DPEHPK3PXP",
                "otpauthUrl": "otpauth://totp/APAD:AUS:maria",
                "qrCodeDataUrl": "data:image/png;base64,iVBORw0KGgo=",
            })
        if route in (("POST", "/users/2fa/enable"), ("POST", "/users/2fa/verify")):
            if body.get("code") != VALID_CODE:
                return httpx.Response(401, json={"error": "Invalid two-factor code."})
            if route[1].endswith("enable"):
                if not user.get("pending"):
                    return httpx.Response(400, json={"error": "Call /users/2fa/setup first."})
                user["totp"] = True
            elif not user.get("totp"):
                return httpx.Response(400, json={"error": "Two-factor authentication is not set up yet."})
            return httpx.Response(200, json={"accessToken": "access." + user["username"], "user": self._safe(user)})
        return httpx.Response(404, json={"error": "Not found."})

    def _safe(self, user):
        return {
            "id": user["id"], "username": user["username"], "agencyCode": user["agencyCode"],
            "agencyName": "Austin", "twoFactorEnabled": user.get("totp", False),
            "createdAt": "2026-11-08T12:00:00.000Z",
        }

    def _register(self, body):
        username = body.get("username", "").strip().lower()
        if len(body.get("password", "")) < 8 or body.get("agencyCode") not in ("AUS", "DAL", "TEX"):
            return httpx.Response(400, json={"errors": ["Password must be between 8 and 72 characters long."]})
        if username in self.users:
            return httpx.Response(409, json={"error": "Username already exists."})
        user = {"id": self.next_id, "username": username, "password": body["password"],
                "agencyCode": body["agencyCode"]}
        self.next_id += 1
        self.users[username] = user
        return httpx.Response(201, json={"user": self._safe(user)})

    def _login(self, body):
        user = self.users.get(str(body.get("username", "")).strip().lower())
        if user is None or user["password"] != body.get("password"):
            return httpx.Response(401, json={"error": "Invalid username or password."})
        return httpx.Response(200, json={
            "mfaToken": "mfa." + user["username"],
            "nextStep": "2fa_verify" if user.get("totp") else "2fa_setup",
        })

    def _user_for_mfa(self, token):
        if not token.startswith("mfa."):
            return None
        return self.users.get(token.removeprefix("mfa."))
