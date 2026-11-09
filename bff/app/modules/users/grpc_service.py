import asyncio

import grpc
import httpx

from app.core.upstream import HTTP_TO_GRPC, upstream_message
from proto import users_pb2 as pb
from proto import users_pb2_grpc as pb_grpc

from .store import UserExistsError


def _user(user):
    return pb.User(user_id=user["user_id"], username=user["username"], org_id=user["org_id"])


class LocalUsers:
    def __init__(self, store):
        self.store = store

    async def register(self, username, password, org_id, client_ip=""):
        try:
            return await asyncio.to_thread(self.store.add, username, password, org_id)
        except UserExistsError as error:
            raise UsersError(grpc.StatusCode.ALREADY_EXISTS, "That username is already taken") from error

    async def login(self, username, password, client_ip=""):
        user = await asyncio.to_thread(self.store.verify, username, password)
        if user is None:
            raise UsersError(grpc.StatusCode.UNAUTHENTICATED, "Invalid username or password")
        return {"user": user}

    async def setup_two_factor(self, mfa_token, client_ip=""):
        raise UsersError(grpc.StatusCode.FAILED_PRECONDITION, "Two-factor sign-in is not used in local mode")

    async def complete_two_factor(self, mfa_token, code, enroll, client_ip=""):
        raise UsersError(grpc.StatusCode.FAILED_PRECONDITION, "Two-factor sign-in is not used in local mode")


class UsersError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class UsersService(pb_grpc.UsersServiceServicer):
    def __init__(self, backend):
        self.backend = backend

    async def _execute(self, context, operation):
        try:
            return await operation()
        except UsersError as error:
            await context.abort(error.code, error.message)
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            await context.abort(
                HTTP_TO_GRPC.get(status, grpc.StatusCode.UNKNOWN),
                upstream_message(error.response, f"Users API returned HTTP {status}"),
            )
        except httpx.TimeoutException:
            await context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, "Users API timed out")
        except httpx.RequestError:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Users API is unavailable")
        except (KeyError, TypeError, ValueError):
            await context.abort(grpc.StatusCode.INTERNAL, "Unexpected Users API response")

    async def SignUp(self, request, context):
        if not all([request.username.strip(), request.password, request.org_id.strip()]):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Username, password and organization are required",
            )

        async def operation():
            user = await self.backend.register(
                request.username, request.password, request.org_id, request.client_ip
            )
            return pb.UserResponse(user=_user(user))

        return await self._execute(context, operation)

    async def Login(self, request, context):
        async def operation():
            result = await self.backend.login(request.username, request.password, request.client_ip)
            if "user" in result:
                return pb.LoginResponse(user=_user(result["user"]))
            return pb.LoginResponse(mfa_token=result["mfa_token"], next_step=result["next_step"])

        return await self._execute(context, operation)

    async def SetupTwoFactor(self, request, context):
        async def operation():
            result = await self.backend.setup_two_factor(request.mfa_token, request.client_ip)
            return pb.TwoFactorSetupResponse(
                qr_code_data_url=result["qr_code_data_url"], secret=result["secret"]
            )

        return await self._execute(context, operation)

    async def CompleteTwoFactor(self, request, context):
        async def operation():
            user = await self.backend.complete_two_factor(
                request.mfa_token, request.code, request.enroll, request.client_ip
            )
            return pb.UserResponse(user=_user(user))

        return await self._execute(context, operation)
