import asyncio
import logging

import grpc

from app.core.config import get_settings
from app.modules.projects.grpc_service import ProjectsService
from app.modules.projects.rest_client import ProjectsRestClient
from app.modules.hardware.grpc_service import HardwareService
from app.modules.hardware.rest_client import HardwareRestClient
from proto import projects_pb2_grpc, hardware_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrpcRuntime:
    def __init__(self, server, projects_client, hardware_client):
        self.server = server
        self.projects_client = projects_client
        self.hardware_client = hardware_client

    async def close(self):
        await self.server.stop(grace=5)
        await self.projects_client.close()
        if self.hardware_client is not None:
            await self.hardware_client.close()


async def start_grpc_runtime():
    """Start the internal gRPC server and return a handle used for shutdown."""
    settings = get_settings()

    if not settings.projects_api_base_url:
        raise ValueError("PROJECTS_API_BASE_URL is required")

    projects_client = ProjectsRestClient(
        base_url=settings.projects_api_base_url,
        timeout=settings.projects_api_timeout,
    )

    hardware_client = None
    server = grpc.aio.server()

    try:
        projects_pb2_grpc.add_ProjectsServiceServicer_to_server(
            ProjectsService(projects_client), server
        )

        if settings.hardware_api_base_url and settings.hardware_api_key:
            hardware_client = HardwareRestClient(
                base_url=settings.hardware_api_base_url,
                api_key=settings.hardware_api_key,
                timeout=settings.hardware_api_timeout,
            )
            hardware_pb2_grpc.add_HardwareServiceServicer_to_server(
                HardwareService(hardware_client), server
            )
            logger.info("HardwareService enabled")
        else:
            logger.warning("HardwareService disabled: URL or API key is missing")

        address = f"{settings.grpc_host}:{settings.grpc_port}"
        if server.add_insecure_port(address) == 0:
            raise RuntimeError(f"Cannot bind gRPC server to {address}")

        await server.start()
        logger.info("gRPC server listening on %s", address)
        return GrpcRuntime(server, projects_client, hardware_client)

    except Exception:
        await server.stop(grace=0)
        await projects_client.close()
        if hardware_client is not None:
            await hardware_client.close()
        raise


async def serve():
    runtime = await start_grpc_runtime()
    try:
        await runtime.server.wait_for_termination()
    finally:
        await runtime.close()


if __name__ == "__main__":
    asyncio.run(serve())
