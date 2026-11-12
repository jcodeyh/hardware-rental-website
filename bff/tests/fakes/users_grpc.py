import grpc

from proto import users_pb2 as pb
from proto import users_pb2_grpc as pb_grpc

VALID_CODE = "123456"
AGENCIES = {"AUS": "Austin", "DAL": "Dallas", "TEX": "Texas"}


class FakeUsersService(pb_grpc.UsersServiceServicer):
    """In-memory stand-in for the Users team's UsersService (same users.proto)."""

    def __init__(self):
        self.users = {}
        self.calls = []

    def _safe(self, user):
        return pb.User(
            id=user["id"],
            username=user["username"],
            agency_code=user["agency_code"],
            agency_name=AGENCIES[user["agency_code"]],
            two_factor_enabled=user.get("totp", False),
            created_at="2026-11-08T12:00:00Z",
        )

    async def _user_for_mfa(self, mfa_token, context):
        user = None
        if mfa_token.startswith("mfa."):
            user = self.users.get(mfa_token.removeprefix("mfa."))
        if user is None:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Missing or invalid authorization token."
            )
        return user

    async def Register(self, request, context):
        self.calls.append("Register")
        username = request.username.strip().lower()
        if len(request.password) < 8 or request.agency_code not in AGENCIES:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Password must be between 8 and 72 characters long.",
            )
        if username in self.users:
            await context.abort(grpc.StatusCode.ALREADY_EXISTS, "Username already exists.")
        user = {
            "id": f"u_{username}",
            "username": username,
            "password": request.password,
            "agency_code": request.agency_code,
        }
        self.users[username] = user
        return pb.RegisterResponse(user=self._safe(user))

    async def Login(self, request, context):
        self.calls.append("Login")
        user = self.users.get(request.username.strip().lower())
        if user is None or user["password"] != request.password:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid username or password")
        return pb.LoginResponse(
            mfa_token=f"mfa.{user['username']}",
            next_step="2fa_verify" if user.get("totp") else "2fa_setup",
        )

    async def SetupTwoFactor(self, request, context):
        self.calls.append("SetupTwoFactor")
        user = await self._user_for_mfa(request.mfa_token, context)
        user["pending"] = True
        return pb.SetupTwoFactorResponse(
            secret="JBSWY3DPEHPK3PXP",
            otpauth_url=f"otpauth://totp/APAD:{user['username']}",
            qr_code_data_url="data:image/png;base64,iVBORw0KGgo=",
        )

    async def _finish(self, request, context, enroll):
        user = await self._user_for_mfa(request.mfa_token, context)
        if request.code != VALID_CODE:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid two-factor code.")
        if enroll:
            if not user.get("pending"):
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT, "Call SetupTwoFactor first."
                )
            user["totp"] = True
        elif not user.get("totp"):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "Two-factor authentication is not set up yet."
            )
        return pb.AuthResponse(access_token=f"access.{user['username']}", user=self._safe(user))

    async def EnableTwoFactor(self, request, context):
        self.calls.append("EnableTwoFactor")
        return await self._finish(request, context, enroll=True)

    async def VerifyTwoFactor(self, request, context):
        self.calls.append("VerifyTwoFactor")
        return await self._finish(request, context, enroll=False)