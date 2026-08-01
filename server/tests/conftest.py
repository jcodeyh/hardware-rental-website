import pytest
from app import app

@pytest.fixture # This fixture sets up a test client for the Flask application, allowing tests to make requests to the app without running a live server
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"

    with app.test_client() as client: # Create a test client for the Flask application
        yield client 