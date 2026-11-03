import asyncio
import grpc

from proto import hardware_pb2 as pb
from proto import hardware_pb2_grpc as services


async def main():
    async with grpc.aio.insecure_channel("127.0.0.1:50052") as channel:
        stub = services.HardwareServiceStub(channel)
        try:
            result = await stub.ListHardware(
                pb.ListHardwareRequest(page=1, size=20), timeout=30,
            )
            print("SUCCESS: gRPC -> BFF Docker -> Hardware REST (Azure)")
            print(f"Total: {result.total}; page: {result.page}; size: {result.size}")
            for item in result.items:
                print(f"{item.id} | {item.name} | {item.category} | available={item.available}")
        except grpc.aio.AioRpcError as error:
            print("gRPC STATUS:", error.code())
            print("DETAILS:", error.details())
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
