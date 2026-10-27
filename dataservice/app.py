"""Dashboard data service (requirements section 9).

MINIMAL VERSION FOR THE TUESDAY VERTICAL SLICE -- Atenea owns this service;
written to the section 9 contract so the slice can run. Please review.

Endpoints (served both with and without the /api/data prefix, because the
gateway strips the prefix -- section 10.2 -- but local dev may not):
  GET /api/data/governments
  GET /api/data/governments/<government>/summary?from=YYYY-MM-DD&to=YYYY-MM-DD
"""
import logging
import time
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from flask import Blueprint, Flask, jsonify, request

NOT_AVAILABLE = "not available"
MIN_PURCHASES_FOR_PRICE = 3
GOVERNMENTS_CACHE_SECONDS = 600

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
        except BadRequest as exc:
            return fail(str(exc), 400)
        if date_from and date_to and date_from > date_to:
            return fail("'from' must be on or before 'to'.", 400)

        data = repository.summary(name, date_from, date_to)

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
            "message": f"No purchase data for {name} in this date range." if empty else "",
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
