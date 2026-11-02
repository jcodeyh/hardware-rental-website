
import grpc
import httpx
import pytest

from app.modules.hardware.grpc_service import HardwareService
from app.modules.hardware.rest_client import HardwareRestClient

from proto import hardware_pb2 as pb
from proto import hardware_pb2_grpc as pb_grpc


@pytest.mark.asyncio
async def test_hardware_grpc_rest():
    requests_seen = []

    def handler(request):
        requests_seen.append(request)

        assert request.method == "GET"
        assert request.url.path == "/api/hardware"
        assert request.url.params["page"] == "1"
        assert request.url.params["size"] == "20"
        assert (
            request.headers.get("cookie")
            == "__Host-hardware=test-session"
        )

        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "_id": "HW001",
                        "name": "Laptop",
                        "category": "Computers",
                        "asset_tag": "LAP-001",
                        "status": "active",
                        "total": 20,
                        "out": 5,
                        "reserved": 2,
                        "version": 1,
                        "available": 13,
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
            },
        )

    rest_client = HardwareRestClient(
        base_url="https://hardware.example.test",
        session_cookie="test-session",
        transport=httpx.MockTransport(handler),
    )

    server = grpc.aio.server()

    pb_grpc.add_HardwareServiceServicer_to_server(
        HardwareService(rest_client),
        server,
    )

    port = server.add_insecure_port("127.0.0.1:0")
    assert port > 0

    await server.start()

    try:
        async with grpc.aio.insecure_channel(
            f"127.0.0.1:{port}"
        ) as channel:
            stub = pb_grpc.HardwareServiceStub(channel)

            result = await stub.ListHardware(
                pb.ListHardwareRequest(page=1, size=20)
            )

            assert result.total == 1
            assert result.items[0].id == "HW001"
            assert result.items[0].name == "Laptop"
            assert result.items[0].available == 13

        assert len(requests_seen) == 1

    finally:
        await server.stop(grace=0)
        await rest_client.close()
