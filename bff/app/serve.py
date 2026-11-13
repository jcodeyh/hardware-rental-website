import asyncio
import logging

import grpc
import uvicorn

from app.core.config import get_settings
from app.grpc_server import start_grpc_runtime
from app.modules.users.grpc_client import UsersGrpcClient
from app.modules.vendors.grpc_client import VendorsGrpcClient
from app.http_api import app


async def main():
    settings = get_settings()
    # Both services run in the same container, and the HTTP bridge is the only public listener.
    if settings.grpc_host not in ("127.0.0.1", "localhost"):
        raise ValueError("For the HTTP bridge, set GRPC_HOST=127.0.0.1")
    if not settings.session_secret:
        raise ValueError("SESSION_SECRET is required")
    runtime = await start_grpc_runtime()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{settings.grpc_port}")
    app.state.grpc_channel = channel
    if not settings.users_grpc_target:
        raise ValueError("USERS_GRPC_TARGET is required")
    users = UsersGrpcClient(
        settings.users_grpc_target,
        timeout=settings.users_timeout,
        use_tls=settings.users_grpc_tls,
    )
    app.state.users = users

    if not settings.vendors_grpc_target:
        raise ValueError("VENDORS_GRPC_TARGET is required")
    vendors = VendorsGrpcClient(
        settings.vendors_grpc_target,
        timeout=settings.vendors_timeout,
        use_tls=settings.vendors_grpc_tls,
    )
    app.state.vendors = vendors

    try:
        server = uvicorn.Server(
            uvicorn.Config(app, host="0.0.0.0", port=8002, log_level="info")
        )
        await server.serve()
    finally:
        await vendors.close()
        await users.close()
        await channel.close()
        await runtime.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
