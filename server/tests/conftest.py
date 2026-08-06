"""Shared test fixtures.

These tests run against the real MongoDB cluster named in .env, so they see the
collection's $jsonSchema validator -- which is what makes them able to catch
type mismatches that an in-memory fake would silently accept. Every document a
test creates is removed again by the `clean_projects` / `test_user` fixtures.

If credentials are missing or the cluster is unreachable (e.g. CI without
secrets configured) the whole suite skips rather than fails.
"""
import pytest

pymongo = pytest.importorskip("pymongo")


@pytest.fixture(scope="session")
def db():
    """Live handle to the test database, or skip if we cannot reach it."""
    try:
        from database.db import db as database

        # ping forces an actual connection; MongoClient() alone is lazy
        database.client.admin.command("ping")
    except Exception as exc:  # noqa: BLE001 - any failure here means "can't test"
        pytest.skip(f"MongoDB unavailable, skipping integration tests: {exc}")
    return database


@pytest.fixture
def client(db):
    """Flask test client."""
    from app import app

    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def clean_projects(db):
    """Delete any project document created during the test."""
    before = {doc["_id"] for doc in db.projects.find({}, {"_id": 1})}
    yield
    db.projects.delete_many({"_id": {"$nin": list(before)}})


@pytest.fixture
def test_user(db):
    """A real user document, removed afterwards."""
    result = db.users.insert_one({
        "username": "pytest-user",
        "password": "not-a-real-hash",
        "projects": [],
    })
    yield {"_id": result.inserted_id, "username": "pytest-user"}
    db.users.delete_one({"_id": result.inserted_id})


@pytest.fixture
def auth_client(client, test_user):
    """Test client with a logged-in session, matching what /login sets."""
    with client.session_transaction() as sess:
        sess["username"] = test_user["username"]
        sess["user_id"] = str(test_user["_id"])
    return client
