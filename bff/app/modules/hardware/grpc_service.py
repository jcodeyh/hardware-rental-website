import grpc

from proto import hardware_pb2 as pb
from proto import hardware_pb2_grpc as pb_grpc


class HardwareService(pb_grpc.HardwareServiceServicer):
    def __init__(self, client):
        self.client = client

    async def _execute(self, context, operation):
        try:
            return await operation()
        except grpc.aio.AioRpcError as error:
            if error.code() == grpc.StatusCode.UNAUTHENTICATED:
                await context.abort(
                    grpc.StatusCode.INTERNAL,
                    "The Hardware service rejected our team credentials",
                )
            await context.abort(
                error.code(),
                error.details() or "Hardware service request failed",
            )

    async def ListHardware(self, request, context):
        page = request.page or 1
        size = request.size or 20
        if page < 1 or not 1 <= size <= 100:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid pagination parameters")

        async def operation():
            data = await self.client.list_hardware(
                page=page, size=size, category=request.category, status=request.status
            )
            return pb.ListHardwareResponse(
                items=[
                    pb.HardwareItem(
                        id=item.id,
                        name=item.name,
                        category=item.category,
                        asset_tag=item.asset_tag,
                        status=item.status,
                        total=item.total,
                        out=item.out,
                        reserved=item.reserved,
                        version=item.version,
                        available=item.available,
                    )
                    for item in data.items
                ],
                total=data.total,
                page=data.page,
                size=data.size,
            )

        return await self._execute(context, operation)

    async def CheckOut(self, request, context):
        await self._validate_action(request, context)

        async def operation():
            await self.client.create_checkout(
                hardware_id=request.hardware_id,
                project_id=request.project_id,
                user_id=request.user_id,
                quantity=request.quantity,
                reason=f"Checked out through the website by {request.user_id}",
                request_id=request.request_id,
            )
            return pb.HardwareActionResponse(success=True)

        return await self._execute(context, operation)

    async def CheckIn(self, request, context):
        await self._validate_action(request, context)

        async def operation():
            checkouts = await self.client.list_checkouts(
                project_id=request.project_id,
                hardware_id=request.hardware_id,
                outstanding=True,
            )
            held = sum(checkout.outstanding for checkout in checkouts)
            if request.quantity > held:
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    f"This project only holds {held} of that hardware",
                )

            remaining = request.quantity
            for checkout in checkouts:
                if remaining == 0:
                    break
                quantity = min(remaining, checkout.outstanding)
                if quantity <= 0:
                    continue
                await self.client.return_checkout(
                    checkout_id=checkout.id,
                    quantity=quantity,
                    reason=f"Checked in through the website by {request.user_id}",
                    request_id=f"{request.request_id}.{checkout.id}",
                )
                remaining -= quantity
            return pb.HardwareActionResponse(success=True)

        return await self._execute(context, operation)

    async def GetProjectHardware(self, request, context):
        if not request.project_id.strip():
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Project ID is required")

        async def operation():
            allocations = await self.client.list_allocations(request.project_id)
            hardware = await self.client.get_many([a.hardware_id for a in allocations])
            return pb.GetProjectHardwareResponse(
                items=[
                    pb.ProjectHardware(
                        hardware_id=a.hardware_id,
                        name=_name(hardware, a.hardware_id),
                        category=_category(hardware, a.hardware_id),
                        reserved=a.quantity,
                        out=a.out,
                    )
                    for a in allocations
                ]
            )

        return await self._execute(context, operation)

    async def ReserveHardware(self, request, context):
        if (
            not request.hardware_id.strip()
            or not request.project_id.strip()
            or not request.request_id.strip()
            or request.quantity < 0
        ):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Hardware, project, quantity and request ID are required",
            )

        async def operation():
            await self.client.allocate(
                hardware_id=request.hardware_id,
                project_id=request.project_id,
                quantity=request.quantity,
                reason=f"Reserved for a new project by {request.user_id or 'the website'}",
                request_id=request.request_id,
            )
            return pb.HardwareActionResponse(success=True)

        return await self._execute(context, operation)

    async def GetUserHardware(self, request, context):
        if not request.user_id.strip():
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "User ID is required")

        async def operation():
            checkouts = await self.client.list_checkouts(
                user_id=request.user_id, outstanding=False
            )
            totals = {}
            for checkout in checkouts:
                quantity, outstanding = totals.get(checkout.hardware_id, (0, 0))
                totals[checkout.hardware_id] = (
                    quantity + checkout.quantity,
                    outstanding + checkout.outstanding,
                )
            hardware = await self.client.get_many(list(totals))
            return pb.GetUserHardwareResponse(
                items=[
                    pb.UserHardware(
                        hardware_id=hardware_id,
                        name=_name(hardware, hardware_id),
                        category=_category(hardware, hardware_id),
                        quantity=quantity,
                        outstanding=outstanding,
                    )
                    for hardware_id, (quantity, outstanding) in totals.items()
                ]
            )

        return await self._execute(context, operation)

    async def _validate_action(self, request, context):
        if (
            not request.hardware_id.strip()
            or not request.project_id.strip()
            or not request.user_id.strip()
            or not request.request_id.strip()
            or request.quantity <= 0
        ):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Hardware, project, user, quantity and request ID are required",
            )


def _name(hardware, hardware_id):
    item = hardware.get(hardware_id)
    return item.name if item is not None and item.name else hardware_id


def _category(hardware, hardware_id):
    item = hardware.get(hardware_id)
    return item.category if item is not None else ""
