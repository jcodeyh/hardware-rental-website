import asyncio

import grpc

from proto import users_pb2 as pb
from proto import users_pb2_grpc as pb_grpc

from .store import UserExistsError


def _to_response(user):
    return pb.UserResponse(
        user=pb.User(
            user_id=user["user_id"],
            username=user["username"],
            org_id=user["org_id"],
        )
    )


class UsersService(pb_grpc.UsersServiceServicer):
    def __init__(self, store):
        self.store = store

    async def SignUp(self, request, context):
        if not all([request.username.strip(), request.password, request.org_id.strip()]):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Username, password and organization are required",
            )
        try:
            user = await asyncio.to_thread(
                self.store.add,
                request.username,
                request.password,
                request.org_id,
            )
        except UserExistsError:
            await context.abort(
                grpc.StatusCode.ALREADY_EXISTS,
                "That username is already taken",
            )
        return _to_response(user)

    async def Login(self, request, context):
        user = await asyncio.to_thread(
            self.store.verify,
            request.username,
            request.password,
        )
        if user is None:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED,
                "Invalid username or password",
            )
        return _to_response(user)
