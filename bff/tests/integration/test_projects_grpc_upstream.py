import grpc
import pytest
import pytest_asyncio

from app.modules.projects.grpc_client import ProjectsGrpcClient
from app.modules.projects.grpc_service import ProjectsService
from proto import projects_pb2 as pb
from proto import projects_pb2_grpc as pb_grpc
from proto.upstream import projects_pb2 as upb
from proto.upstream import projects_pb2_grpc as upb_grpc


class FakeProjectsUpstream(upb_grpc.ProjectsServiceServicer):
    def __init__(self):
        self.projects = {}
        self.search_requests = []

    async def CreateProject(self, request, context):
        key = (request.org_id, request.project_id)
        if key in self.projects:
            await context.abort(grpc.StatusCode.ALREADY_EXISTS, "Project already exists")
        project = upb.Project(
            org_id=request.org_id,
            project_id=request.project_id,
            project_name=request.project_name,
            project_desc=request.project_desc,
            creator_id=request.creator_id,
            budget=request.budget,
            hardware_list=request.hardware_list,
            joined_users=[request.creator_id],
        )
        self.projects[key] = project
        return upb.CreateProjectResponse()

    async def JoinProject(self, request, context):
        project = self.projects.get((request.org_id, request.project_id))
        if project is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Project not found")
        if request.user_id in project.joined_users:
            await context.abort(grpc.StatusCode.ALREADY_EXISTS, "User already joined")
        project.joined_users.append(request.user_id)
        return upb.MembershipResponse()

    async def LeaveProject(self, request, context):
        project = self.projects.get((request.org_id, request.project_id))
        if project is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Project not found")
        if request.user_id not in project.joined_users:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "User is not a member")
        project.joined_users.remove(request.user_id)
        return upb.MembershipResponse()

    async def SearchProjects(self, request, context):
        self.search_requests.append(request)
        return upb.SearchProjectsResponse(project_list=[
            upb.ProjectSummary(
                project_id=p.project_id,
                project_name=p.project_name,
                org_id=p.org_id,
                joined_users=p.joined_users,
            )
            for p in self.projects.values()
            if (not request.HasField("org_id") or p.org_id == request.org_id)
            and (not request.HasField("user_id") or request.user_id in p.joined_users)
        ])

    async def GetProject(self, request, context):
        project = self.projects.get((request.org_id, request.project_id))
        if project is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Project not found")
        return upb.GetProjectResponse(project_info=project)

    async def GetUnitPrice(self, request, context):
        return upb.GetUnitPriceResponse(
            category=request.category,
            austin=upb.SourceUnitPrice(
                available=True,
                stats=upb.PriceStats(median=443, low=117, high=1281.26, purchases=3585),
            ),
            dallas=upb.SourceUnitPrice(available=False),
            texas=upb.SourceUnitPrice(available=False),
        )

    async def GetDepartmentSpend(self, request, context):
        await context.abort(grpc.StatusCode.UNAVAILABLE, "price data is unavailable right now")

    async def GetBudgetContext(self, request, context):
        return upb.GetBudgetContextResponse(
            org_id=request.org_id,
            budget=request.budget,
            unpriced_items=len(request.items),
        )


@pytest_asyncio.fixture
async def bff():
    fake = FakeProjectsUpstream()
    upstream = grpc.aio.server()
    upb_grpc.add_ProjectsServiceServicer_to_server(fake, upstream)
    upstream_port = upstream.add_insecure_port("127.0.0.1:0")
    await upstream.start()

    client = ProjectsGrpcClient(target=f"127.0.0.1:{upstream_port}", timeout=5)
    server = grpc.aio.server()
    pb_grpc.add_ProjectsServiceServicer_to_server(ProjectsService(client), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")

    try:
        yield fake, pb_grpc.ProjectsServiceStub(channel)
    finally:
        await channel.close()
        await server.stop(grace=0)
        await client.close()
        await upstream.stop(grace=0)


async def _create(stub, project_id="P001"):
    return await stub.CreateProject(pb.CreateProjectRequest(
        creator_id="u_alice",
        project_id=project_id,
        project_name="Office Equipment",
        project_desc="Purchase office hardware",
        org_id="AUS",
        budget=5000,
        hardware_list=[pb.HardwareItem(hardware_id="HW001", allocation=2)],
    ))


@pytest.mark.asyncio
async def test_project_lifecycle_through_upstream_grpc(bff):
    fake, stub = bff

    created = await _create(stub)
    assert created.success

    joined = await stub.JoinProject(
        pb.ProjectMembershipRequest(project_id="P001", org_id="AUS", user_id="u_bob")
    )
    assert joined.success

    found = await stub.SearchProjects(pb.SearchProjectsRequest(org_id="AUS"))
    assert [p.project_id for p in found.project_list] == ["P001"]
    assert fake.search_requests[-1].org_id == "AUS"
    assert not fake.search_requests[-1].HasField("project_id")

    assert fake.projects[("AUS", "P001")].joined_users == ["u_alice", "u_bob"]

    info = (await stub.GetProject(pb.GetProjectRequest(project_id="P001", org_id="AUS"))).project_info
    assert info.creator_id == "u_alice"
    assert info.project_desc == "Purchase office hardware"
    assert info.budget == 5000
    assert [(h.hardware_id, h.allocation) for h in info.hardware_list] == [("HW001", 2)]

    left = await stub.LeaveProject(
        pb.ProjectMembershipRequest(project_id="P001", org_id="AUS", user_id="u_bob")
    )
    assert left.success


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call, code",
    [
        (lambda stub: _create(stub), grpc.StatusCode.ALREADY_EXISTS),
        (
            lambda stub: stub.GetProject(pb.GetProjectRequest(project_id="nope", org_id="AUS")),
            grpc.StatusCode.NOT_FOUND,
        ),
        (
            lambda stub: stub.LeaveProject(
                pb.ProjectMembershipRequest(project_id="P001", org_id="AUS", user_id="u_carol")
            ),
            grpc.StatusCode.FAILED_PRECONDITION,
        ),
        (
            lambda stub: stub.GetDepartmentSpend(pb.DepartmentSpendRequest(keyword="laptop")),
            grpc.StatusCode.UNAVAILABLE,
        ),
    ],
)
async def test_upstream_status_codes_pass_through(bff, call, code):
    _, stub = bff
    await _create(stub)

    with pytest.raises(grpc.aio.AioRpcError) as error:
        await call(stub)

    assert error.value.code() == code
    assert error.value.details()


@pytest.mark.asyncio
async def test_unit_price_returns_upstream_fields(bff):
    _, stub = bff

    result = await stub.GetUnitPrice(pb.UnitPriceRequest(category="Laptops"))

    assert result["category"] == "Laptops"
    assert result["austin"]["available"] is True
    assert result["austin"]["stats"]["median"] == 443
    assert result["dallas"]["available"] is False
