import base64
from dataclasses import dataclass, field

import grpc

from proto.upstream import hardware_pb2 as pb
from proto.upstream import hardware_pb2_grpc as pb_grpc

TEAM = "front-end"
CODE = "fake-team-code"
MAX_PAGE_SIZE = 2


def expected_authorization():
    return "Basic " + base64.b64encode(f"{TEAM}:{CODE}".encode()).decode()


@dataclass
class State:
    hardware: dict = field(default_factory=dict)
    allocations: dict = field(default_factory=dict)
    checkouts: dict = field(default_factory=dict)
    requests: dict = field(default_factory=dict)
    calls: list = field(default_factory=list)
    fail_next: dict = field(default_factory=dict)


def _page(items, request):
    page = request.page if request.HasField("page") else 1
    size = min(request.size if request.HasField("size") else 20, MAX_PAGE_SIZE)
    start = (page - 1) * size
    return items[start:start + size], len(items), page, size


class FakeHardwareUpstream(pb_grpc.HardwareServiceServicer):
    def __init__(self, state=None):
        self.state = state or State()

    def add_hardware(self, hardware_id, name, category, total):
        self.state.hardware[hardware_id] = pb.Hardware(
            id=hardware_id, name=name, category=category, asset_tag=f"TAG-{hardware_id}",
            status="active", total=total, reserved=0, out=0, version=1,
            available=total, unallocated=total,
        )

    async def _enter(self, name, request, context):
        self.state.calls.append((name, request))
        metadata = dict(context.invocation_metadata())
        if metadata.get("authorization") != expected_authorization():
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "missing or wrong credentials")
        failure = self.state.fail_next.pop(name, None)
        if failure is not None:
            await context.abort(*failure)

    async def _replay(self, request, context):
        if not request.HasField("request_id"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "request_id is required")
        key = request.request_id
        seen = self.state.requests.get(key)
        if seen is None:
            return None
        fields, response = seen
        if fields != request.SerializeToString(deterministic=True):
            await context.abort(grpc.StatusCode.ALREADY_EXISTS, "request_id reused with different fields")
        return response

    def _remember(self, request, response):
        self.state.requests[request.request_id] = (request.SerializeToString(deterministic=True), response)
        return response

    def _hardware(self, hardware_id):
        return self.state.hardware.get(hardware_id)

    def _refresh(self, hardware):
        hardware.available = hardware.total - hardware.out
        hardware.unallocated = hardware.total - hardware.reserved
        hardware.version += 1

    async def ListHardware(self, request, context):
        await self._enter("ListHardware", request, context)
        items = sorted(self.state.hardware.values(), key=lambda h: h.name.lower())
        if request.HasField("category"):
            items = [h for h in items if h.category == request.category]
        chunk, total, page, size = _page(items, request)
        return pb.ListHardwareResponse(items=chunk, total=total, page=page, size=size)

    async def GetHardware(self, request, context):
        await self._enter("GetHardware", request, context)
        hardware = self._hardware(request.hardware_id)
        if hardware is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "unknown hardware id")
        return hardware

    async def AllocateHardware(self, request, context):
        await self._enter("AllocateHardware", request, context)
        replay = await self._replay(request, context)
        if replay is not None:
            return replay
        if not request.reason or not request.HasField("quantity"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "quantity and reason are required")
        hardware = self._hardware(request.hardware_id)
        if hardware is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "unknown hardware id")
        key = f"{request.hardware_id}:{request.project_id}"
        allocation = self.state.allocations.get(key) or pb.Allocation(
            id=key, hardware_id=request.hardware_id, project_id=request.project_id
        )
        new_reserved = hardware.reserved - allocation.quantity + request.quantity
        if request.quantity < allocation.out or new_reserved > hardware.total:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "not enough unallocated stock")
        hardware.reserved = new_reserved
        allocation.quantity = request.quantity
        allocation.version += 1
        self.state.allocations[key] = allocation
        self._refresh(hardware)
        return self._remember(request, hardware)

    async def ListAllocations(self, request, context):
        await self._enter("ListAllocations", request, context)
        items = [
            a for a in self.state.allocations.values()
            if (not request.HasField("project_id") or a.project_id == request.project_id)
            and (not request.HasField("hardware_id") or a.hardware_id == request.hardware_id)
        ]
        chunk, total, page, size = _page(items, request)
        return pb.ListAllocationsResponse(items=chunk, total=total, page=page, size=size)

    async def CreateCheckout(self, request, context):
        await self._enter("CreateCheckout", request, context)
        replay = await self._replay(request, context)
        if replay is not None:
            return replay
        if not request.reason or request.quantity <= 0:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "quantity and reason are required")
        allocation = self.state.allocations.get(f"{request.hardware_id}:{request.project_id}")
        if allocation is None or allocation.quantity - allocation.out < request.quantity:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "not enough reserved stock")
        hardware = self._hardware(request.hardware_id)
        checkout_id = f"co{len(self.state.checkouts) + 1}"
        checkout = pb.Checkout(
            id=checkout_id, project_id=request.project_id, hardware_id=request.hardware_id,
            user_id=request.user_id, quantity=request.quantity, returned=0, version=1,
            outstanding=request.quantity,
        )
        self.state.checkouts[checkout_id] = checkout
        allocation.out += request.quantity
        hardware.out += request.quantity
        self._refresh(hardware)
        return self._remember(request, checkout)

    async def ListCheckouts(self, request, context):
        await self._enter("ListCheckouts", request, context)
        outstanding_only = request.outstanding if request.HasField("outstanding") else True
        items = [
            c for c in self.state.checkouts.values()
            if (not request.HasField("project_id") or c.project_id == request.project_id)
            and (not request.HasField("hardware_id") or c.hardware_id == request.hardware_id)
            and (not request.HasField("user_id") or c.user_id == request.user_id)
            and (not outstanding_only or c.outstanding > 0)
        ]
        chunk, total, page, size = _page(items, request)
        return pb.ListCheckoutsResponse(items=chunk, total=total, page=page, size=size)

    async def ReturnCheckout(self, request, context):
        await self._enter("ReturnCheckout", request, context)
        replay = await self._replay(request, context)
        if replay is not None:
            return replay
        checkout = self.state.checkouts.get(request.checkout_id)
        if checkout is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "unknown checkout id")
        if request.quantity <= 0 or request.quantity > checkout.outstanding:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "cannot return more than is out")
        checkout.returned += request.quantity
        checkout.outstanding -= request.quantity
        checkout.version += 1
        allocation = self.state.allocations[f"{checkout.hardware_id}:{checkout.project_id}"]
        allocation.out -= request.quantity
        hardware = self._hardware(checkout.hardware_id)
        hardware.out -= request.quantity
        self._refresh(hardware)
        return self._remember(request, checkout)


async def start_fake_hardware():
    upstream = FakeHardwareUpstream()
    server = grpc.aio.server()
    pb_grpc.add_HardwareServiceServicer_to_server(upstream, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    return upstream, server, f"127.0.0.1:{port}"
