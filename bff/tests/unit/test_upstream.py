import httpx

from app.core.upstream import upstream_message


def test_reads_every_error_key_the_teams_use():
    cases = [
        ({"success": False, "errorMessage": "Project not found"}, "Project not found"),
        ({"success": False, "message": "items list cannot be empty"}, "items list cannot be empty"),
        ({"error": "Invalid two-factor code."}, "Invalid two-factor code."),
        ({"errors": ["Agency code must be AUS, DAL, or TEX.", "Bad password."]},
         "Agency code must be AUS, DAL, or TEX. Bad password."),
        ({"detail": "Not Found"}, "Not Found"),
        ({"detail": [{"msg": "field required"}]}, "fallback"),
    ]
    for body, expected in cases:
        assert upstream_message(httpx.Response(400, json=body), "fallback") == expected
    assert upstream_message(httpx.Response(502, text="<html>"), "fallback") == "fallback"
