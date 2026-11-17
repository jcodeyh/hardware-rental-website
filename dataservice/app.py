"""Dashboard data service (requirements section 9).

MINIMAL VERSION FOR THE TUESDAY VERTICAL SLICE -- Atenea owns this service;
written to the section 9 contract so the slice can run. Please review.

Endpoints (served both with and without the /api/data prefix, because the
gateway strips the prefix -- section 10.2 -- but local dev may not):
  GET /api/data/governments
  GET /api/data/governments/<government>/summary?from=YYYY-MM-DD&to=YYYY-MM-DD&match=laptop,monitor
"""
import logging
import re
import time
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from flask import Blueprint, Flask, jsonify, request

NOT_AVAILABLE = "not available"
MIN_PURCHASES_FOR_PRICE = 3
GOVERNMENTS_CACHE_SECONDS = 600
MAX_MATCH_TERMS = 10
MATCH_TERM = re.compile(r"^[a-z0-9][a-z0-9 &/-]{1,39}$")
SYNONYMS = {
    "laptop": ["notebook"],
    "notebook": ["laptop"],
    "desktop": ["microcomputer", "computer"],
    "computer": ["microcomputer"],
    "pc": ["microcomputer", "computer"],
    "monitor": ["display"],
    "display": ["monitor"],
    "phone": ["telephone"],
    "smartphone": ["telephone", "phone"],
    "router": ["network"],
    "switch": ["network"],
    "projector": ["audio visual", "audiovisual"],
    "headset": ["audio"],
    "drone": ["unmanned aircraft"],
}

log = logging.getLogger("dataservice")


def money(value):
    if value is None:
        return NOT_AVAILABLE
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def iso_day(value):
    if value is None:
        return None
    return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()


def parse_day(text, name):
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise BadRequest(f"'{name}' must be a date in the format YYYY-MM-DD.")


def parse_match(text):
    if not text:
        return [], []
    terms = []
    for raw in text.split(","):
        term = " ".join(raw.lower().split())
        if not term or term in terms:
            continue
        if not MATCH_TERM.match(term):
            raise BadRequest(f"'match' terms must be 2 to 40 letters or numbers; got '{raw.strip()}'.")
        terms.append(term)
    if len(terms) > MAX_MATCH_TERMS:
        raise BadRequest(f"'match' takes at most {MAX_MATCH_TERMS} terms.")
    keywords = []
    for term in terms:
        singular = term[:-1] if len(term) > 3 and term.endswith("s") and not term.endswith("ss") else term
        for keyword in [singular, *SYNONYMS.get(singular, [])]:
            if keyword not in keywords:
                keywords.append(keyword)
    return terms, keywords


MAX_BUDGET_ITEMS = 20
MAX_ITEM_WORDS = 6
MAX_QUANTITY = 1_000_000
STOPWORDS = {"and", "or", "of", "the", "for", "with", "to", "in", "on", "per", "an", "new"}


def item_word_groups(description):
    groups = []
    seen = set()
    for word in re.findall(r"[a-z0-9]+", description.lower()):
        if len(word) < 2 or word in STOPWORDS or word in seen:
            continue
        seen.add(word)
        singular = word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word
        group = [singular] + [s for s in SYNONYMS.get(singular, []) if s != singular]
        groups.append(group)
        if len(groups) == MAX_ITEM_WORDS:
            break
    return groups


def best_category(groups, candidates):
    best = None
    for c in candidates:
        if c["purchases"] < MIN_PURCHASES_FOR_PRICE:
            continue
        name = c["category"].lower()
        score = sum(1 for g in groups if any(k in name for k in g))
        typed = sum(1 for g in groups if g[0] in name)
        key = (score, typed, c["purchases"])
        if score and (best is None or key > best[0]):
            best = (key, c["category"])
    return best[1] if best else None


def parse_budget_body(body):
    if not isinstance(body, dict):
        raise BadRequest("Send a JSON body with 'budget' and 'items'.")
    budget = body.get("budget")
    if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not 0 <= budget <= 1e12:
        raise BadRequest("'budget' must be a number of 0 or more.")
    items = body.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_BUDGET_ITEMS:
        raise BadRequest(f"'items' must list 1 to {MAX_BUDGET_ITEMS} items.")
    parsed = []
    for i, item in enumerate(items, start=1):
        description = item.get("description") if isinstance(item, dict) else None
        quantity = item.get("quantity") if isinstance(item, dict) else None
        if not isinstance(description, str) or not 1 <= len(description.strip()) <= 80:
            raise BadRequest(f"Item {i} needs a description of 1 to 80 characters.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAX_QUANTITY:
            raise BadRequest(f"Item {i} needs a whole-number quantity of 1 or more.")
        parsed.append({"description": description.strip(), "quantity": quantity})
    return float(budget), parsed


class BadRequest(Exception):
    pass


def fail(message, status):
    return jsonify({"success": False, "message": message}), status


def create_app(repository=None):
    if repository is None:
        from db import SqlRepository
        repository = SqlRepository()

    app = Flask(__name__)
    app.json.sort_keys = False
    cache = {"at": 0.0, "governments": None}

    def known_governments():
        if cache["governments"] is None or time.time() - cache["at"] > GOVERNMENTS_CACHE_SECONDS:
            cache["governments"] = repository.governments()
            cache["at"] = time.time()
        return cache["governments"]

    bp = Blueprint("data", __name__)

    @bp.get("/governments")
    def governments():
        rows = known_governments()
        return jsonify({
            "success": True,
            "governments": [
                {"government": g["government"], "records": g["records"],
                 "from": iso_day(g["first_date"]), "to": iso_day(g["last_date"])}
                for g in rows if g["records"] > 0
            ],
            "message": "" if rows else "No government data is loaded yet.",
        })

    @bp.get("/governments/<government>/summary")
    def summary(government):
        names = {g["government"].lower(): g["government"] for g in known_governments()}
        name = names.get(government.lower())
        if name is None:
            return fail(f"Unknown government '{government}'. Known: {', '.join(sorted(names.values()))}.", 404)
        try:
            date_from = parse_day(request.args.get("from"), "from")
            date_to = parse_day(request.args.get("to"), "to")
            terms, keywords = parse_match(request.args.get("match"))
        except BadRequest as exc:
            return fail(str(exc), 400)
        if date_from and date_to and date_from > date_to:
            return fail("'from' must be on or before 'to'.", 400)

        data = repository.summary(name, date_from, date_to, keywords=keywords or None)

        typical_prices = []
        for c in data["categories"]:
            p = data["prices"].get(c["category"])
            enough = p is not None and p["purchases"] >= MIN_PURCHASES_FOR_PRICE
            typical_prices.append({
                "category": c["category"],
                "median": money(p["median"]) if enough else NOT_AVAILABLE,
                "low": money(p["low"]) if enough else NOT_AVAILABLE,
                "high": money(p["high"]) if enough else NOT_AVAILABLE,
                "purchases": p["purchases"] if p else 0,
            })

        empty = not data["categories"]
        return jsonify({
            "success": True,
            "government": name,
            "from": iso_day(date_from),
            "to": iso_day(date_to),
            "match": terms,
            "priceBasis": data["price_basis"],
            "topCategories": [
                {"category": c["category"], "purchases": c["purchases"], "totalAmount": money(c["total_amount"])}
                for c in data["categories"]
            ],
            "typicalPrices": typical_prices,
            "topVendors": [
                {"vendor": v["vendor"], "purchases": v["purchases"], "totalAmount": money(v["total_amount"])}
                for v in data["vendors"]
            ],
            "message": (
                f"No {name} purchases match {', '.join(terms)} in this date range." if empty and terms
                else f"No purchase data for {name} in this date range." if empty else ""
            ),
        })

    @bp.post("/governments/<government>/budget")
    def budget_estimate(government):
        names = {g["government"].lower(): g["government"] for g in known_governments()}
        name = names.get(government.lower())
        if name is None:
            return fail(f"Unknown government '{government}'. Known: {', '.join(sorted(names.values()))}.", 404)
        body = request.get_json(silent=True)
        try:
            budget, items = parse_budget_body(body)
            date_from = parse_day(body.get("from"), "from")
            date_to = parse_day(body.get("to"), "to")
        except BadRequest as exc:
            return fail(str(exc), 400)
        if date_from and date_to and date_from > date_to:
            return fail("'from' must be on or before 'to'.", 400)

        base = {"success": True, "government": name, "from": iso_day(date_from), "to": iso_day(date_to),
                "budget": money(budget)}
        if not repository.has_unit_price(name):
            return jsonify({
                **base,
                "priceBasis": "payment",
                "items": [{**i, "matchedCategory": None, "unitPrice": NOT_AVAILABLE, "estimatedCost": NOT_AVAILABLE}
                          for i in items],
                "totalEstimate": NOT_AVAILABLE,
                "withinBudget": None,
                "unpricedItems": [i["description"] for i in items],
                "message": f"{name} publishes payments, not unit prices, so item costs can't be estimated. "
                           "Pick a government with unit prices.",
            })

        groups = [item_word_groups(i["description"]) for i in items]
        candidates = repository.price_candidates(name, date_from, date_to,
                                                 [[k for g in gs for k in g] for gs in groups])
        matched = [best_category(gs, cs) for gs, cs in zip(groups, candidates)]
        prices = repository.category_prices(name, date_from, date_to, sorted({m for m in matched if m}))

        result_items, unpriced = [], []
        total = {"low": 0.0, "typical": 0.0, "high": 0.0}
        for item, category in zip(items, matched):
            p = prices.get(category) if category else None
            if p is None or p["purchases"] < MIN_PURCHASES_FOR_PRICE:
                unpriced.append(item["description"])
                result_items.append({**item, "matchedCategory": category,
                                     "unitPrice": NOT_AVAILABLE, "estimatedCost": NOT_AVAILABLE})
                continue
            raw = {"low": p["low"] * item["quantity"], "typical": p["median"] * item["quantity"],
                   "high": p["high"] * item["quantity"]}
            for k in total:
                total[k] += raw[k]
            cost = {k: money(v) for k, v in raw.items()}
            result_items.append({**item, "matchedCategory": category,
                                 "unitPrice": {"median": money(p["median"]), "low": money(p["low"]),
                                               "high": money(p["high"]), "purchases": p["purchases"]},
                                 "estimatedCost": cost})

        priced_any = len(unpriced) < len(items)
        total_estimate = {k: money(v) for k, v in total.items()} if priced_any else NOT_AVAILABLE
        return jsonify({
            **base,
            "priceBasis": "unitPrice",
            "items": result_items,
            "totalEstimate": total_estimate,
            "withinBudget": (round(total["typical"], 2) <= budget) if not unpriced else None,
            "unpricedItems": unpriced,
            "message": "",
        })

    app.register_blueprint(bp, url_prefix="/api/data")
    app.register_blueprint(bp, url_prefix="", name="data_root")

    @app.get("/healthz")
    def healthz():
        return jsonify({"success": True})

    @app.errorhandler(404)
    def not_found(_):
        return fail("Not found.", 404)

    @app.errorhandler(Exception)
    def unexpected(exc):
        log.exception("request failed")
        return fail("The data service could not read the database. Try again in a minute.", 503)

    return app


if __name__ == "__main__":
    create_app().run(port=8001, debug=True)
