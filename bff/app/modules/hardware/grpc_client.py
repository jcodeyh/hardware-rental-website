import asyncio
import base64

import grpc

from proto.upstream import hardware_pb2 as pb
from proto.upstream import hardware_pb2_grpc as pb_grpc

PAGE_SIZE = 100
MAX_PAGES = 50


class HardwareGrpcClient:
    def __init__(
        self,
        target: str,
        team: str,
        code: str,
        timeout: float = 15.0,
        use_tls: bool = True,
        channel=None,
    ):
        if not target.strip():
            raise ValueError("HARDWARE_GRPC_TARGET is required")
        if not team.strip() or not code.strip():
            raise ValueError("HARDWARE_TEAM and HARDWARE_TEAM_CODE are required")

        if channel is not None:
            self.channel = channel
        elif use_tls:
            self.channel = grpc.aio.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            self.channel = grpc.aio.insecure_channel(target)

        token = base64.b64encode(f"{team}:{code}".encode()).decode()
        self.metadata = (("authorization", f"Basic {token}"),)
        self.timeout = timeout
        self.stub = pb_grpc.HardwareServiceStub(self.channel)

    async def _call(self, method, request, retry_unavailable=True):
        try:
            return await method(request, metadata=self.metadata, timeout=self.timeout)
        except grpc.aio.AioRpcError as error:
            if not retry_unavailable or error.code() != grpc.StatusCode.UNAVAILABLE:
                raise
        await asyncio.sleep(0.5)
        return await method(request, metadata=self.metadata, timeout=self.timeout)

    async def _all_pages(self, method, request_type, **fields):
        items = []
        for page in range(1, MAX_PAGES + 1):
            result = await self._call(method, request_type(page=page, size=PAGE_SIZE, **fields))
            items.extend(result.items)
            if not result.items or len(items) >= result.total:
                break
        return items

    async def list_hardware(self, page=1, size=20, category="", status=""):
        request = pb.ListHardwareRequest(page=page, size=size)
        if category:
            request.category = category
        if status:
            request.status = status
        return await self._call(self.stub.ListHardware, request)

    async def get_hardware(self, hardware_id):
        return await self._call(
            self.stub.GetHardware, pb.GetHardwareRequest(hardware_id=hardware_id)
        )

    async def get_many(self, hardware_ids):
        unique = list(dict.fromkeys(hardware_ids))
        results = await asyncio.gather(
            *[self.get_hardware(hardware_id) for hardware_id in unique],
            return_exceptions=True,
        )
        found = {}
        for hardware_id, result in zip(unique, results):
            if isinstance(result, grpc.aio.AioRpcError):
                if result.code() != grpc.StatusCode.NOT_FOUND:
                    raise result
                continue
            if isinstance(result, BaseException):
                raise result
            found[hardware_id] = result
        return found

    async def list_allocations(self, project_id):
        return await self._all_pages(
            self.stub.ListAllocations, pb.ListAllocationsRequest, project_id=project_id
        )

    async def list_checkouts(self, project_id="", hardware_id="", user_id="", outstanding=True):
        filters = {"project_id": project_id, "hardware_id": hardware_id, "user_id": user_id}
        return await self._all_pages(
            self.stub.ListCheckouts,
            pb.ListCheckoutsRequest,
            outstanding=outstanding,
            **{key: value for key, value in filters.items() if value},
        )

    async def allocate(self, hardware_id, project_id, quantity, reason, request_id):
        return await self._call(
            self.stub.AllocateHardware,
            pb.AllocateHardwareRequest(
                hardware_id=hardware_id,
                project_id=project_id,
                quantity=quantity,
                reason=reason,
                request_id=request_id,
            ),
        )

    async def create_checkout(self, hardware_id, project_id, user_id, quantity, reason, request_id):
        return await self._call(
            self.stub.CreateCheckout,
            pb.CreateCheckoutRequest(
                hardware_id=hardware_id,
                project_id=project_id,
                user_id=user_id,
                quantity=quantity,
                reason=reason,
                request_id=request_id,
            ),
        )

    async def return_checkout(self, checkout_id, quantity, reason, request_id):
        return await self._call(
            self.stub.ReturnCheckout,
            pb.ReturnCheckoutRequest(
                checkout_id=checkout_id,
                quantity=quantity,
                reason=reason,
                request_id=request_id,
            ),
        )

    async def close(self):
        await self.channel.close()

