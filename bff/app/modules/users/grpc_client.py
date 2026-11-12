import grpc

from proto import users_pb2 as pb
from proto import users_pb2_grpc as pb_grpc


class UsersGrpcClient:
    def __init__(self, target: str, timeout: float = 15.0, use_tls: bool = True, channel=None):
        if not target.strip():
            raise ValueError("USERS_GRPC_TARGET is required")
        if channel is not None:
            self.channel = channel
        elif use_tls:
            self.channel = grpc.aio.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            self.channel = grpc.aio.insecure_channel(target)
        self.timeout = timeout
        self.stub = pb_grpc.UsersServiceStub(self.channel)

    async def register(self, username, password, agency_code):
        return await self.stub.Register(
            pb.RegisterRequest(agency_code=agency_code, username=username, password=password),
            timeout=self.timeout,
        )

    async def login(self, username, password):
        return await self.stub.Login(
            pb.LoginRequest(username=username, password=password), timeout=self.timeout
        )

    async def setup_two_factor(self, mfa_token):
        return await self.stub.SetupTwoFactor(
            pb.SetupTwoFactorRequest(mfa_token=mfa_token), timeout=self.timeout
        )

    async def complete_two_factor(self, mfa_token, code, enroll):
        request = pb.TwoFactorCodeRequest(mfa_token=mfa_token, code=code)
        if enroll:
            return await self.stub.EnableTwoFactor(request, timeout=self.timeout)
        return await self.stub.VerifyTwoFactor(request, timeout=self.timeout)

    
    async def close(self):
        await self.channel.close()