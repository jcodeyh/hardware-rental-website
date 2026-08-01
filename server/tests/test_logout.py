def test_logout_returns_204(client):
    response = client.post("/logout")

    assert response.status_code == 204