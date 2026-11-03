import base64

import grpc
import httpx
import pytest

from app.modules.hardware.grpc_service import HardwareService
from app.modules.hardware.rest_client import HardwareRestClient
from proto import hardware_pb2 as pb
from proto import hardware_pb2_grpc as pb_grpc


@pytest.mark.asyncio
async def test_hardware_grpc_rest_basic_auth():
    requests_seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        assert request.method == "GET"
        assert request.url.path == "/api/hardware"
        assert request.url.params["page"] == "1"
        assert request.url.params["size"] == "20"
        expected = "Basic " + base64.b64encode(b"front-end:fake-test-key").decode()
        assert request.headers["Authorization"] == expected
        return httpx.Response(200, json={
            "items": [{
                "_id": "HW001", "name": "Laptop", "category": "Computers",
                "asset_tag": "LAP-001", "status": "active", "total": 20,
                "out": 5, "reserved": 2, "version": 1, "available": 13,
            }],
            "total": 1, "page": 1, "size": 20,
        })

    client = HardwareRestClient(
        base_url="https://hardware.example.test",
        api_key="fake-test-key",
        transport=httpx.MockTransport(handler),
    )
    server = grpc.aio.server()
    pb_grpc.add_HardwareServiceServicer_to_server(HardwareService(client), server)
    port = server.add_insecure_port("127.0.0.1:0")
    assert port > 0
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = pb_grpc.HardwareServiceStub(channel)
            result = await stub.ListHardware(
                pb.ListHardwareRequest(page=1, size=20), timeout=5
            )
            assert result.total == 1
            assert result.items[0].id == "HW001"
            assert result.items[0].name == "Laptop"
            assert result.items[0].available == 13
        assert len(requests_seen) == 1
    finally:
        await server.stop(grace=0)
        await client.close()


@pytest.mark.asyncio
async def test_hardware_unauthorized_maps_to_grpc():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Unauthorized"})

    client = HardwareRestClient(
        "https://hardware.example.test", "wrong-test-key",
        transport=httpx.MockTransport(handler),
    )
    server = grpc.aio.server()
    pb_grpc.add_HardwareServiceServicer_to_server(HardwareService(client), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = pb_grpc.HardwareServiceStub(channel)
            with pytest.raises(grpc.aio.AioRpcError) as error:
                await stub.ListHardware(pb.ListHardwareRequest(page=1, size=20), timeout=5)
            assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED
    finally:
        await server.stop(grace=0)
        await client.close()


def test_missing_hardware_key_fails_closed():
    with pytest.raises(ValueError, match="HARDWARE_API_KEY"):
        HardwareRestClient("https://hardware.example.test", "")
