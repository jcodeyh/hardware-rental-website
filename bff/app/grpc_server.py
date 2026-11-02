
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


async def serve():
    settings = get_settings()

    if not settings.projects_api_base_url:
        raise ValueError("PROJECTS_API_BASE_URL is required")

    projects_client = ProjectsRestClient(
        base_url=settings.projects_api_base_url,
        timeout=settings.projects_api_timeout,
    )

    hardware_client = None
    server = grpc.aio.server()

    projects_pb2_grpc.add_ProjectsServiceServicer_to_server(
        ProjectsService(projects_client),
        server,
    )

    # Hardware is registered when its URL is configured.
    if settings.hardware_api_base_url:
        hardware_client = HardwareRestClient(
            base_url=settings.hardware_api_base_url,
            timeout=settings.hardware_api_timeout,
        )
        hardware_pb2_grpc.add_HardwareServiceServicer_to_server(
            HardwareService(hardware_client),
            server,
        )
    else:
        logger.warning(
            "Hardware API URL missing; HardwareService disabled"
        )

    address = f"{settings.grpc_host}:{settings.grpc_port}"
    if server.add_insecure_port(address) == 0:
        raise RuntimeError(f"Cannot bind gRPC server to {address}")

    try:
        await server.start()
        logger.info("gRPC server listening on %s", address)
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await projects_client.close()
        if hardware_client:
            await hardware_client.close()


if __name__ == "__main__":
    asyncio.run(serve())
