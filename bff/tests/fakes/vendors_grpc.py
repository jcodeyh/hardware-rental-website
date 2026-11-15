import grpc

from proto import vendors_pb2 as pb
from proto import vendors_pb2_grpc as pb_grpc

VENDORS = {
    "AUS": [("AUS:v1:C:aaa", "ACME SUPPLY"), ("AUS:v1:C:bbb", "BLUE LINE IT")],
    "DAL": [("DAL:v1:C:ccc", "CITY OFFICE CO")],
}


class FakeVendorsService(pb_grpc.VendorDataServiceServicer):
    """In-memory stand-in for the Users team's VendorDataService (same vendors.proto)."""

    def __init__(self, users):
        self.users = users
        self.tokens = []
        self.requests = []
        self.expired = False

    async def _agency(self, context):
        header = dict(context.invocation_metadata()).get("authorization", "")
        token = header.removeprefix("Bearer ")
        self.tokens.append(token)
        user = None
        if token.startswith("access."):
            user = self.users.users.get(token.removeprefix("access."))
        if self.expired or user is None:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Token or account is not authorized."
            )
        return user["agency_code"]

    async def ListVendors(self, request, context):
        agency = await self._agency(context)
        self.requests.append(request)
        if request.government and request.government != agency:
            await context.abort(
                grpc.StatusCode.PERMISSION_DENIED, "Government is not available for this account."
            )
        rows = [row for row in VENDORS.get(agency, []) if request.query.lower() in row[1].lower()]
        size = request.page_size or 20
        page = request.page or 1
        window = rows[(page - 1) * size : page * size]
        return pb.ListVendorsResponse(
            agency_code=agency,
            vendors=[
                pb.Vendor(
                    vendor_id=vendor_id,
                    agency_code=agency,
                    vendor_name=name,
                    identity_method="SOURCE_CODE",
                    record_count="1",
                )
                for vendor_id, name in window
            ],
            total_count=str(len(rows)),
            page=page,
            page_size=size,
            has_next=page * size < len(rows),
        )

    async def GetVendorRecords(self, request, context):
        agency = await self._agency(context)
        self.requests.append(request)
        match = [row for row in VENDORS.get(agency, []) if row[0] == request.vendor_id]
        if not match:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Vendor not found.")
        vendor_id, name = match[0]
        return pb.GetVendorRecordsResponse(
            agency_code=agency,
            vendor=pb.Vendor(
                vendor_id=vendor_id, agency_code=agency, vendor_name=name, record_count="1"
            ),
            records=[
                pb.VendorRecord(
                    vendor_name=name,
                    record_date="2026-10-01",
                    has_record_date=True,
                    description="Laptops",
                    has_description=True,
                    amount="1250.50",
                    has_amount=True,
                    source="purchase_order",
                    record_type="PURCHASE_ORDER",
                )
            ],
            total_records="1",
            page=request.page or 1,
            page_size=request.page_size or 20,
        )