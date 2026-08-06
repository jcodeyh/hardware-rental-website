"""Tests for POST /create_project."""
from bson.objectid import ObjectId


def test_rejects_anonymous_request(client, clean_projects):
    response = client.post("/create_project", json={
        "projectName": "Anon", "description": "d",
    })
    assert response.status_code == 401


def test_creates_project_and_returns_its_id(auth_client, clean_projects, db):
    response = auth_client.post("/create_project", json={
        "projectName": "Robotics Lab", "description": "Arm and sensors",
    })

    assert response.status_code == 201
    project_id = response.get_json()["projectId"]

    stored = db.projects.find_one({"projectId": project_id})
    assert stored is not None
    assert stored["projectName"] == "Robotics Lab"
    assert stored["description"] == "Arm and sensors"


def test_stores_project_id_as_string(auth_client, clean_projects, db):
    """The projects collection's $jsonSchema requires a string projectId.

    An ObjectId here makes every insert fail validation, and it also means
    join_project -- which matches on the string it receives as JSON -- can
    never find the project.
    """
    response = auth_client.post("/create_project", json={
        "projectName": "Type Check", "description": "d",
    })

    stored = db.projects.find_one({"projectId": response.get_json()["projectId"]})
    assert isinstance(stored["projectId"], str)


def test_adds_creator_to_project_members(auth_client, clean_projects, db, test_user):
    """Otherwise the creator gets 403 from get_project_info on their own project."""
    response = auth_client.post("/create_project", json={
        "projectName": "Members", "description": "d",
    })

    stored = db.projects.find_one({"projectId": response.get_json()["projectId"]})
    assert stored["users"] == [test_user["_id"]]


def test_created_project_is_readable_by_its_creator(auth_client, clean_projects):
    """End-to-end: create, then fetch it back through get_project_info."""
    created = auth_client.post("/create_project", json={
        "projectName": "Round Trip", "description": "d",
    })
    project_id = created.get_json()["projectId"]

    response = auth_client.get("/get_project_info", query_string={"projectId": project_id})

    assert response.status_code == 200
    assert response.get_json()["projectName"] == "Round Trip"


def test_created_project_can_be_joined(auth_client, clean_projects, db):
    """join_project matches projectId as a string, so creation must store one."""
    created = auth_client.post("/create_project", json={
        "projectName": "Joinable", "description": "d",
    })
    project_id = created.get_json()["projectId"]

    response = auth_client.post("/join_project", json={"projectId": project_id})

    assert response.status_code == 200


def test_rejects_empty_name(auth_client, clean_projects):
    response = auth_client.post("/create_project", json={
        "projectName": "", "description": "d",
    })
    assert response.status_code == 400


def test_rejects_missing_name(auth_client, clean_projects):
    """`None == ""` is False, so a missing key must be caught on its own."""
    response = auth_client.post("/create_project", json={"description": "d"})
    assert response.status_code == 400


def test_rejects_whitespace_only_name(auth_client, clean_projects):
    response = auth_client.post("/create_project", json={
        "projectName": "   ", "description": "d",
    })
    assert response.status_code == 400


def test_defaults_missing_description_to_empty_string(auth_client, clean_projects, db):
    """description is required by the schema and must be a string, not None."""
    response = auth_client.post("/create_project", json={"projectName": "No Desc"})

    assert response.status_code == 201
    stored = db.projects.find_one({"projectId": response.get_json()["projectId"]})
    assert stored["description"] == ""


def test_rejects_request_with_no_json_body(auth_client, clean_projects):
    """Should be a JSON 400, not Flask's HTML error page."""
    response = auth_client.post("/create_project", data="", content_type="application/json")

    assert response.status_code == 400
    assert response.get_json()["error"]


def test_generates_a_distinct_id_per_project(auth_client, clean_projects):
    first = auth_client.post("/create_project", json={"projectName": "A", "description": "d"})
    second = auth_client.post("/create_project", json={"projectName": "A", "description": "d"})

    assert first.get_json()["projectId"] != second.get_json()["projectId"]


def test_new_project_starts_with_no_hardware(auth_client, clean_projects, db):
    response = auth_client.post("/create_project", json={
        "projectName": "Empty HW", "description": "d",
    })

    stored = db.projects.find_one({"projectId": response.get_json()["projectId"]})
    assert stored["hwSets"] == {}


def test_reports_failure_when_the_database_rejects_the_write(
    auth_client, clean_projects, monkeypatch
):
    """A write error must surface as 500, not crash the request."""
    from pymongo.collection import Collection
    from pymongo.errors import PyMongoError

    def boom(*args, **kwargs):
        raise PyMongoError("simulated write failure")

    # Patch the class, not `db.projects`: pymongo builds a fresh Collection
    # object on every attribute access, so patching one instance never sticks.
    monkeypatch.setattr(Collection, "insert_one", boom)

    response = auth_client.post("/create_project", json={
        "projectName": "Doomed", "description": "d",
    })

    assert response.status_code == 500
    assert response.get_json()["error"]


def test_uses_client_supplied_project_id(auth_client, clean_projects, db):
    """The frontend picks the id (e.g. "PROJ-007"), so it must be honoured."""
    response = auth_client.post("/create_project", json={
        "projectId": "PYTEST-007", "projectName": "Client Id", "description": "d",
    })

    assert response.status_code == 201
    assert response.get_json()["projectId"] == "PYTEST-007"
    assert db.projects.find_one({"projectId": "PYTEST-007"}) is not None


def test_rejects_duplicate_project_id(auth_client, clean_projects):
    """projectId carries a unique index; a collision is the caller's fault."""
    payload = {"projectId": "PYTEST-DUP", "projectName": "First", "description": "d"}
    assert auth_client.post("/create_project", json=payload).status_code == 201

    response = auth_client.post("/create_project", json=payload)

    assert response.status_code == 409
    assert response.get_json()["error"]


def test_unknown_object_id_is_not_accepted_as_a_project_id(auth_client, clean_projects):
    """Sanity check that join_project 404s rather than matching loosely."""
    response = auth_client.post("/join_project", json={"projectId": str(ObjectId())})
    assert response.status_code == 404
