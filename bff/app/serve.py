import asyncio
import logging

import grpc
import uvicorn

from app.core.config import get_settings
from app.grpc_server import start_grpc_runtime
from app.http_api import app


async def main():
    settings = get_settings()
    # Both services run in the same container, and the HTTP bridge is the only public listener.
    if settings.grpc_host not in ("127.0.0.1", "localhost"):
        raise ValueError("For the HTTP bridge, set GRPC_HOST=127.0.0.1")
    runtime = await start_grpc_runtime()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{settings.grpc_port}")
    app.state.grpc_channel = channel
    try:
        server = uvicorn.Server(
            uvicorn.Config(app, host="0.0.0.0", port=8002, log_level="info")
        )
        await server.serve()
    finally:
        await channel.close()
        await runtime.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
