import grpc

from proto import vendors_pb2 as pb
from proto import vendors_pb2_grpc as pb_grpc


class VendorsGrpcClient:
    def __init__(self, target: str, timeout: float = 15.0, use_tls: bool = True, channel=None):
        if not target.strip():
            raise ValueError("VENDORS_GRPC_TARGET is required")
        if channel is not None:
            self.channel = channel
        elif use_tls:
            self.channel = grpc.aio.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            self.channel = grpc.aio.insecure_channel(target)
        self.timeout = timeout
        self.stub = pb_grpc.VendorDataServiceStub(self.channel)

    def _metadata(self, access_token):
        return (("authorization", f"Bearer {access_token}"),)

    async def list_vendors(self, access_token, query="", page=1, page_size=20):
        # government is left empty on purpose: the service then uses the agency
        # verified from the access token.
        return await self.stub.ListVendors(
            pb.ListVendorsRequest(government="", query=query, page=page, page_size=page_size),
            metadata=self._metadata(access_token),
            timeout=self.timeout,
        )

    async def get_vendor_records(self, access_token, vendor_id, page=1, page_size=20):
        return await self.stub.GetVendorRecords(
            pb.GetVendorRecordsRequest(
                government="", vendor_id=vendor_id, page=page, page_size=page_size
            ),
            metadata=self._metadata(access_token),
            timeout=self.timeout,
        )

    async def close(self):
        await self.channel.close()