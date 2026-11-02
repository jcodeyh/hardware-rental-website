
import grpc
import httpx

from proto import hardware_pb2 as pb
from proto import hardware_pb2_grpc as pb_grpc


class HardwareService(pb_grpc.HardwareServiceServicer):
    def __init__(self, client):
        self.client = client

    async def ListHardware(self, request, context):
        page = request.page or 1
        size = request.size or 20

        if page < 1 or not 1 <= size <= 100:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid pagination parameters",
            )

        try:
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
                        available=item.get("available", 0),
                    )
                    for item in data["items"]
                ],
                total=data["total"],
                page=data["page"],
                size=data["size"],
            )

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            codes = {
                401: grpc.StatusCode.UNAUTHENTICATED,
                403: grpc.StatusCode.PERMISSION_DENIED,
                404: grpc.StatusCode.NOT_FOUND,
                422: grpc.StatusCode.INVALID_ARGUMENT,
                503: grpc.StatusCode.UNAVAILABLE,
            }

            await context.abort(
                codes.get(status, grpc.StatusCode.UNKNOWN),
                f"Hardware API returned HTTP {status}",
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
