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


class BudgetRepository(FakeRepository):
    def __init__(self):
        super().__init__()
        self.candidate_calls = []
        self.price_calls = []

    def has_unit_price(self, government):
        return government != "Dallas"

    def price_candidates(self, government, date_from, date_to, keyword_lists):
        self.candidate_calls.append((government, date_from, date_to, keyword_lists))
        table = [
            {"category": "COMPUTER ACCESSORIES AND SUPPLIES", "purchases": 3796},
            {"category": "Microcomputers, Handheld, Laptop, and Notebook", "purchases": 410},
            {"category": "Monitors, Color and Monochrome", "purchases": 1972},
            {"category": "D082 Adult defibrillation / monitor combination pads", "purchases": 53},
            {"category": "Laptop Bags", "purchases": 2},
        ]
        return [[c for c in table if any(k in c["category"].lower() for k in kws)] for kws in keyword_lists]

    def category_prices(self, government, date_from, date_to, categories):
        self.price_calls.append(categories)
        known = {
            "Microcomputers, Handheld, Laptop, and Notebook": {"purchases": 410, "median": 900.0, "low": 800.0, "high": 1200.004},
            "Monitors, Color and Monochrome": {"purchases": 1972, "median": 192.29, "low": 154.94, "high": 297.34},
        }
        return {c: known[c] for c in categories if c in known}


@pytest.fixture
def budget_client():
    repo = BudgetRepository()
    return create_app(repo).test_client(), repo


def test_budget_matches_most_words_then_most_purchases(budget_client):
    client, repo = budget_client
    body = client.post("/api/data/governments/austin/budget", json={
        "budget": 20000, "from": "2020-01-01", "to": "2026-10-31",
        "items": [{"description": "Laptop computers", "quantity": 10}, {"description": "monitor", "quantity": 5}],
    }).get_json()
    assert body["success"] is True
    assert body["government"] == "Austin"
    laptop, monitor = body["items"]
    assert laptop["matchedCategory"] == "Microcomputers, Handheld, Laptop, and Notebook"
    assert laptop["estimatedCost"] == {"low": 8000.0, "typical": 9000.0, "high": 12000.04}
    assert laptop["unitPrice"]["purchases"] == 410
    assert monitor["matchedCategory"] == "Monitors, Color and Monochrome"
    assert body["totalEstimate"] == {"low": 8774.7, "typical": 9961.45, "high": 13486.74}
    assert body["withinBudget"] is True
    assert body["unpricedItems"] == []
    gov, date_from, date_to, keyword_lists = repo.candidate_calls[0]
    assert (gov, date_from, date_to) == ("Austin", date(2020, 1, 1), date(2026, 10, 31))
    assert keyword_lists[0] == ["laptop", "notebook", "computer", "microcomputer"]
    assert keyword_lists[1] == ["monitor", "display"]


def test_budget_unmatched_item_makes_verdict_unknown(budget_client):
    client, _ = budget_client
    body = client.post("/governments/Austin/budget", json={
        "budget": 100, "items": [{"description": "monitor", "quantity": 1}, {"description": "Water", "quantity": 10}],
    }).get_json()
    water = body["items"][1]
    assert water["matchedCategory"] is None
    assert water["estimatedCost"] == "not available"
    assert body["unpricedItems"] == ["Water"]
    assert body["withinBudget"] is None
    assert body["totalEstimate"]["typical"] == 192.29


def test_budget_over_budget(budget_client):
    client, _ = budget_client
    body = client.post("/governments/austin/budget", json={
        "budget": 100, "items": [{"description": "laptop", "quantity": 1}],
    }).get_json()
    assert body["withinBudget"] is False


def test_budget_skips_categories_with_too_few_purchases(budget_client):
    client, _ = budget_client
    body = client.post("/governments/austin/budget", json={
        "budget": 100, "items": [{"description": "bags", "quantity": 1}],
    }).get_json()
    assert body["items"][0]["matchedCategory"] is None
    assert body["totalEstimate"] == "not available"


def test_budget_payment_only_government(budget_client):
    client, repo = budget_client
    body = client.post("/governments/dallas/budget", json={
        "budget": 100, "items": [{"description": "laptop", "quantity": 1}],
    }).get_json()
    assert body["priceBasis"] == "payment"
    assert body["withinBudget"] is None
    assert "payments, not unit prices" in body["message"]
    assert repo.candidate_calls == []


@pytest.mark.parametrize("payload, message", [
    (None, "JSON body"),
    ({"budget": -1, "items": [{"description": "x", "quantity": 1}]}, "'budget'"),
    ({"budget": True, "items": [{"description": "x", "quantity": 1}]}, "'budget'"),
    ({"budget": 1, "items": []}, "'items'"),
    ({"budget": 1, "items": [{"description": " ", "quantity": 1}]}, "Item 1 needs a description"),
    ({"budget": 1, "items": [{"description": "x", "quantity": 1.5}]}, "Item 1 needs a whole-number"),
    ({"budget": 1, "items": [{"description": "x", "quantity": 1}], "from": "2026-02-01", "to": "2026-01-01"}, "'from'"),
])
def test_budget_rejects_bad_input(budget_client, payload, message):
    client, _ = budget_client
    response = client.post("/governments/austin/budget", json=payload) if payload is not None else \
        client.post("/governments/austin/budget", data="nope", content_type="application/json")
    assert response.status_code == 400
    assert message in response.get_json()["message"]


def test_budget_unknown_government(budget_client):
    client, _ = budget_client
    response = client.post("/governments/houston/budget", json={"budget": 1, "items": [{"description": "x", "quantity": 1}]})
    assert response.status_code == 404


def test_best_category_prefers_the_typed_word_over_synonyms():
    from app import best_category, item_word_groups
    groups = item_word_groups("desktop pc")
    candidates = [
        {"category": "COMPUTER ACCESSORIES AND SUPPLIES", "purchases": 3796},
        {"category": "Microcomputers, Desktop or Towerbased", "purchases": 583},
    ]
    assert best_category(groups, candidates) == "Microcomputers, Desktop or Towerbased"


def test_item_word_groups_drops_stopwords_and_duplicates():
    from app import item_word_groups
    assert item_word_groups("Chairs for the office, office") == [["chair"], ["office"]]
