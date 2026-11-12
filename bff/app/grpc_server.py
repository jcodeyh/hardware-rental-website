
import asyncio
import logging

import grpc

from app.core.config import get_settings
from app.modules.hardware.grpc_client import HardwareGrpcClient
from app.modules.hardware.grpc_service import HardwareService
from app.modules.projects.grpc_service import ProjectsService
from app.modules.projects.rest_client import ProjectsRestClient
from proto import hardware_pb2_grpc, projects_pb2_grpc

logger = logging.getLogger(__name__)


class GrpcRuntime:
    def __init__(self, server, clients):
        self.server = server
        self.clients = clients

    async def close(self):
        await self.server.stop(grace=5)
        for client in self.clients:
            await client.close()


async def start_grpc_runtime():
    settings = get_settings()

    if not settings.projects_api_base_url:
        raise ValueError("PROJECTS_API_BASE_URL is required")

    clients = []
    server = grpc.aio.server()

    try:
        projects_client = ProjectsRestClient(
            base_url=settings.projects_api_base_url,
            timeout=settings.projects_api_timeout,
            hardware_item_field=settings.projects_hardware_field,
        )
        clients.append(projects_client)

        projects_pb2_grpc.add_ProjectsServiceServicer_to_server(
            ProjectsService(projects_client),
            server,
        )

        if settings.hardware_grpc_target and settings.hardware_team_code:
            hardware_client = HardwareGrpcClient(
                target=settings.hardware_grpc_target,
                team=settings.hardware_team,
                code=settings.hardware_team_code,
                timeout=settings.hardware_timeout,
                use_tls=settings.hardware_grpc_tls,
            )
            clients.append(hardware_client)

            hardware_pb2_grpc.add_HardwareServiceServicer_to_server(
                HardwareService(hardware_client),
                server,
            )
            logger.info(
                "HardwareService: %s",
                settings.hardware_grpc_target,
            )
        else:
            logger.warning(
                "HardwareService disabled: HARDWARE_GRPC_TARGET "
                "or HARDWARE_TEAM_CODE is missing"
            )

        address = f"{settings.grpc_host}:{settings.grpc_port}"

        if server.add_insecure_port(address) == 0:
            raise RuntimeError(f"Cannot bind gRPC server to {address}")

        await server.start()
        logger.info("gRPC server listening on %s", address)

        return GrpcRuntime(server, clients)

    except Exception:
        await server.stop(grace=0)

        for client in clients:
            await client.close()

        raise


async def serve():
    runtime = await start_grpc_runtime()

    try:
        await runtime.server.wait_for_termination()
    finally:
        await runtime.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
