
import grpc
import httpx

from app.core.upstream import upstream_message
from proto import hardware_pb2 as pb
from proto import hardware_pb2_grpc as pb_grpc


HTTP_TO_GRPC = {
    400: grpc.StatusCode.INVALID_ARGUMENT,
    401: grpc.StatusCode.UNAUTHENTICATED,
    403: grpc.StatusCode.PERMISSION_DENIED,
    404: grpc.StatusCode.NOT_FOUND,
    409: grpc.StatusCode.FAILED_PRECONDITION,
    422: grpc.StatusCode.INVALID_ARGUMENT,
    429: grpc.StatusCode.RESOURCE_EXHAUSTED,
    502: grpc.StatusCode.UNAVAILABLE,
    503: grpc.StatusCode.UNAVAILABLE,
    504: grpc.StatusCode.DEADLINE_EXCEEDED,
}


def _available(item):
    if "available" in item:
        return item["available"]
    return max(item["total"] - item["out"] - item["reserved"], 0)


def _outstanding(checkout):
    if "outstanding" in checkout:
        return checkout["outstanding"]
    return checkout["quantity"] - checkout.get("returned", 0)


class HardwareService(pb_grpc.HardwareServiceServicer):
    def __init__(self, client):
        self.client = client

    async def _execute(self, context, operation):
        try:
            return await operation()

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            await context.abort(
                HTTP_TO_GRPC.get(status, grpc.StatusCode.UNKNOWN),
                upstream_message(exc.response, f"Hardware API returned HTTP {status}"),
            )

        except httpx.TimeoutException:
            await context.abort(
                grpc.StatusCode.DEADLINE_EXCEEDED,
                "Hardware API timed out",
            )

        except httpx.RequestError:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Hardware API unavailable",
            )

        except (KeyError, TypeError, ValueError):
            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Invalid Hardware API response",
            )

    async def ListHardware(self, request, context):
        page = request.page or 1
        size = request.size or 20

        if page < 1 or not 1 <= size <= 100:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid pagination parameters",
            )

        async def operation():
            data = await self.client.list_hardware(
                page=page,
                size=size,
                category=request.category,
                status=request.status,
            )

            return pb.ListHardwareResponse(
                items=[
                    pb.HardwareItem(
                        id=item["_id"],
                        name=item["name"],
                        category=item["category"],
                        asset_tag=item["asset_tag"],
                        status=item["status"],
                        total=item["total"],
                        out=item["out"],
                        reserved=item["reserved"],
                        version=item["version"],
                        available=_available(item),
                    )
                    for item in data["items"]
                ],
                total=data["total"],
                page=data["page"],
                size=data["size"],
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
            checkouts = await self.client.list_outstanding_checkouts(
                request.project_id,
                request.hardware_id,
            )
            held = sum(_outstanding(checkout) for checkout in checkouts)
            if request.quantity > held:
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    f"This project only holds {held} of that hardware",
                )

            remaining = request.quantity
            for checkout in checkouts:
                if remaining == 0:
                    break
                quantity = min(remaining, _outstanding(checkout))
                if quantity <= 0:
                    continue
                await self.client.return_checkout(
                    checkout_id=checkout["_id"],
                    quantity=quantity,
                    reason=f"Checked in through the website by {request.user_id}",
                    request_id=f"{request.request_id}.{checkout['_id']}",
                )
                remaining -= quantity
            return pb.HardwareActionResponse(success=True)

        return await self._execute(context, operation)

    async def GetHoldings(self, request, context):
        if not request.project_id.strip():
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Project ID is required",
            )

        async def operation():
            checkouts = await self.client.list_outstanding_checkouts(request.project_id)
            totals = {}
            for checkout in checkouts:
                hardware_id = checkout["hardware_id"]
                totals[hardware_id] = totals.get(hardware_id, 0) + _outstanding(checkout)
            return pb.GetHoldingsResponse(
                holdings=[
                    pb.Holding(hardware_id=hardware_id, quantity=quantity)
                    for hardware_id, quantity in totals.items()
                    if quantity > 0
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
