from datetime import date, datetime

import pytest

from app import create_app


class FakeRepository:
    def __init__(self):
        self.calls = []

    def governments(self):
        return [
            {"government": "Austin", "records": 5, "first_date": datetime(2009, 1, 2), "last_date": datetime(2026, 10, 1)},
            {"government": "Dallas", "records": 3, "first_date": datetime(2025, 10, 1), "last_date": datetime(2026, 10, 20)},
        ]

    def summary(self, government, date_from, date_to, keywords=None):
        self.calls.append((government, date_from, date_to))
        self.keywords = keywords
        if date_from and date_from.year >= 2030:
            return {"price_basis": "unitPrice", "categories": [], "prices": {}, "vendors": []}
        return {
            "price_basis": "unitPrice",
            "categories": [
                {"category": "Laptops", "purchases": 54, "total_amount": 61234.505},
                {"category": "Asphalt", "purchases": 2, "total_amount": None},
            ],
            "prices": {
                "Laptops": {"purchases": 54, "median": 912.0, "low": 780.004, "high": 1150.125},
                "Asphalt": {"purchases": 2, "median": 10.0, "low": 9.0, "high": 11.0},
            },
            "vendors": [{"vendor": "DELL MARKETING LP", "purchases": 162, "total_amount": 245000}],
        }


@pytest.fixture
def repo():
    return FakeRepository()


@pytest.fixture
def client(repo):
    return create_app(repo).test_client()


@pytest.mark.parametrize("prefix", ["/api/data", ""])
def test_governments(client, prefix):
    body = client.get(f"{prefix}/governments").get_json()
    assert body["success"] is True
    assert [g["government"] for g in body["governments"]] == ["Austin", "Dallas"]
    assert body["governments"][0]["from"] == "2009-01-02"


def test_summary_shape_and_price_rules(client, repo):
    body = client.get("/api/data/governments/austin/summary?from=2020-01-01&to=2026-10-23").get_json()
    assert body["success"] is True
    assert body["government"] == "Austin"
    assert (body["from"], body["to"]) == ("2020-01-01", "2026-10-23")
    assert repo.calls == [("Austin", date(2020, 1, 1), date(2026, 10, 23))]
    assert body["topCategories"][0] == {"category": "Laptops", "purchases": 54, "totalAmount": 61234.51}
    assert body["topCategories"][1]["totalAmount"] == "not available"
    laptops, asphalt = body["typicalPrices"]
    assert (laptops["median"], laptops["low"], laptops["high"]) == (912.0, 780.0, 1150.13)
    # fewer than 3 purchases -> not available
    assert (asphalt["median"], asphalt["low"], asphalt["high"]) == ("not available",) * 3
    assert body["topVendors"][0]["totalAmount"] == 245000.0
    assert body["message"] == ""


def test_summary_empty_is_success_with_message(client):
    body = client.get("/governments/Dallas/summary?from=2031-01-01").get_json()
    assert body["success"] is True
    assert body["topCategories"] == [] and body["typicalPrices"] == [] and body["topVendors"] == []
    assert body["message"] == "No purchase data for Dallas in this date range."


def test_unknown_government(client):
    resp = client.get("/api/data/governments/Houston/summary")
    assert resp.status_code == 404
    assert resp.get_json()["success"] is False


@pytest.mark.parametrize("query", ["from=2020-13-01", "to=yesterday", "from=2025-01-02&to=2025-01-01"])
def test_bad_dates(client, query):
    resp = client.get(f"/api/data/governments/Austin/summary?{query}")
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_database_error_is_json(repo):
    def boom(*_):
        raise RuntimeError("db down")
    repo.summary = boom
    resp = create_app(repo).test_client().get("/api/data/governments/Austin/summary")
    assert resp.status_code == 503
    assert resp.get_json()["success"] is False


def test_match_expands_hardware_types_to_purchase_keywords(client, repo):
    body = client.get("/api/data/governments/Austin/summary?match=Laptops, Monitor ,laptops").get_json()
    assert body["success"] is True
    assert body["match"] == ["laptops", "monitor"]
    assert repo.keywords == ["laptop", "notebook", "monitor", "display"]


def test_no_match_means_no_keyword_filter(client, repo):
    body = client.get("/api/data/governments/Austin/summary").get_json()
    assert body["match"] == []
    assert repo.keywords is None


@pytest.mark.parametrize("query", ["match=x", "match=" + ",".join(f"type{i}" for i in range(11)), "match=a%25b"])
def test_bad_match(client, query):
    resp = client.get(f"/api/data/governments/Austin/summary?{query}")
    assert resp.status_code == 400
    assert "match" in resp.get_json()["message"]


def test_empty_match_message_names_the_terms(client, repo):
    repo.summary = lambda *a, **k: {"price_basis": "unitPrice", "categories": [], "prices": {}, "vendors": []}
    body = client.get("/api/data/governments/Dallas/summary?match=drone").get_json()
    assert body["message"] == "No Dallas purchases match drone in this date range."


def test_category_match_sql_is_parameterized_and_escaped():
    from db import _sql_top_vendors, category_match
    clause, params = category_match(["laptop", "50%_off[x]"])
    assert clause == " AND (LOWER(category) LIKE ? ESCAPE '\\' OR LOWER(category) LIKE ? ESCAPE '\\')"
    assert params == ["%laptop%", "%50\\%\\_off\\[x]%"]
    assert category_match(None) == ("", [])
    assert clause in _sql_top_vendors(clause)
