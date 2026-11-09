from app.modules.projects.mapper import budget_context_to_json, create_to_json, project_to_proto
from proto import projects_pb2 as pb


def test_create_sends_allocation_and_legacy_capacity():
    request = pb.CreateProjectRequest(
        creator_id="1", project_id="P1", project_name="Lab", org_id="AUS", budget=10,
        hardware_list=[pb.HardwareItem(hardware_id="HW001", allocation=4)],
    )
    assert create_to_json(request)["hardwareList"] == [
        {"hardwareId": "HW001", "allocation": 4, "capacity": 4}
    ]
    assert create_to_json(request)["projectDesc"] == ""


def test_project_reads_v5_allocation_and_v4_capacity():
    base = {"projectId": "P1", "projectName": "Lab", "orgId": "AUS"}
    v5 = project_to_proto({**base, "hardwareList": [{"hardwareId": "A", "allocation": 3}]})
    v4 = project_to_proto({**base, "hardwareList": [{"hardwareId": "B", "capacity": 7}]})
    assert v5.hardware_list[0].allocation == 3
    assert v4.hardware_list[0].allocation == 7


def test_budget_context_body_matches_contract():
    request = pb.BudgetContextRequest(
        org_id="AUS", budget=20000,
        items=[pb.BudgetItem(description="LIGHTS, EMERGENCY", quantity=20)],
    )
    assert budget_context_to_json(request) == {
        "orgId": "AUS",
        "budget": 20000.0,
        "items": [{"description": "LIGHTS, EMERGENCY", "quantity": 20}],
    }
