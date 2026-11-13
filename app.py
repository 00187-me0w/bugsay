"""Bugsay: ferry schedules across Cebu, Leyte and Bohol."""

import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for

import data

# Philippine law gives students (RA 11314), seniors (RA 9994) and persons with
# disability (RA 10754) 20% off regular fares. Carriers check ID at the counter.
DISCOUNT_RATE = 0.20
MAX_PASSENGERS = 10
BOOKING_WINDOW_DAYS = 180
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    reference   TEXT PRIMARY KEY,
    trip_id     TEXT NOT NULL,
    travel_date TEXT NOT NULL,
    fare_class  TEXT NOT NULL,
    passengers  INTEGER NOT NULL,
    discounted  INTEGER NOT NULL,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    total       INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS waitlist (
    email       TEXT PRIMARY KEY,
    is_student  INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);
"""

NAV_ITEMS = [
    ("schedules", "Schedules"),
    ("route_map", "Port map"),
    ("updates", "Travel updates"),
    ("tourism", "Explore Visayas"),
    ("rewards", "Rewards"),
]


def fare_total(price, passengers, discounted):
    """Total in whole pesos; discounted passengers pay 80% of the fare."""
    discounted_price = round(price * (1 - DISCOUNT_RATE))
    return price * (passengers - discounted) + discounted_price * discounted


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def new_reference():
    return "BG-" + "".join(secrets.choice(REF_ALPHABET) for _ in range(6))


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "bugsay.sqlite3"),
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    with sqlite3.connect(app.config["DATABASE"]) as conn:
        conn.executescript(SCHEMA)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return resp

    @app.context_processor
    def globals_for_templates():
        return {
            "nav_items": NAV_ITEMS,
            "ports": data.PORTS,
            "today": date.today(),
            "discount_pct": int(DISCOUNT_RATE * 100),
            "max_passengers": MAX_PASSENGERS,
        }

    @app.template_filter("peso")
    def peso(value):
        return f"₱{value:,}"

    # ------------------------------------------------------------- pages

    @app.route("/")
    def home():
        featured = []
        for dest in ("baybay", "hilongos", "ormoc"):
            trips = data.trips_for_route("cebu", dest)
            if trips:
                cheapest = min(trips, key=data.min_fare)
                featured.append({"key": dest, "trip": data.serialize_trip(cheapest),
                                 "count": len(trips)})
        return render_template("index.html", featured=featured,
                               advisories=data.ADVISORIES[:2],
                               routes=data.route_map())

    @app.route("/schedules")
    def schedules():
        return render_template("schedules.html", routes=data.route_map(),
                               query=request.args)

    @app.route("/updates")
    def updates():
        return render_template("updates.html", advisories=data.ADVISORIES)

    @app.route("/faq")
    def faq():
        return render_template("faq.html")

    @app.route("/map")
    def route_map():
        port_list = [{"key": k, **v} for k, v in data.PORTS.items()]
        departures = {k: len([t for t in data.TRIPS if t["origin"] == k]) for k in data.PORTS}
        return render_template("map.html", port_list=port_list, lines=data.route_lines(),
                               departures=departures)

    @app.route("/rewards")
    def rewards():
        return render_template("rewards.html")

    @app.route("/tourism")
    def tourism():
        return render_template("tourism.html", destinations=data.DESTINATIONS)

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/my-trip")
    def booking_lookup():
        ref = (request.args.get("ref") or "").strip().upper()
        if ref:
            if not ref.startswith("BG-"):
                ref = "BG-" + ref
            return redirect(url_for("booking_detail", reference=ref))
        return render_template("my_trip.html")

    @app.route("/booking/<reference>")
    def booking_detail(reference):
        row = get_db().execute("SELECT * FROM bookings WHERE reference = ?",
                               (reference.upper(),)).fetchone()
        if row is None:
            return render_template("my_trip.html", not_found=reference), 404
        trip = data.TRIPS_BY_ID.get(row["trip_id"])
        if trip is None:
            abort(404)
        return render_template("booking.html", booking=row, trip=data.serialize_trip(trip),
                               travel_date=date.fromisoformat(row["travel_date"]))

    # --------------------------------------------------------------- API

    @app.get("/api/routes")
    def api_routes():
        return jsonify({"ports": data.PORTS, "routes": data.route_map()})

    @app.get("/api/trips")
    def api_trips():
        origin = request.args.get("origin", "")
        destination = request.args.get("destination", "")
        if origin not in data.PORTS or destination not in data.PORTS:
            return jsonify({"error": "Unknown port."}), 400
        if origin == destination:
            return jsonify({"error": "Origin and destination must be different."}), 400

        trips = data.trips_for_route(origin, destination)
        day = parse_date(request.args.get("date"))
        if request.args.get("date") and day is None:
            return jsonify({"error": "Date must be YYYY-MM-DD."}), 400

        running = [t for t in trips if day is None or data.runs_on(t, day)]
        other_days = [t for t in trips if t not in running]
        return jsonify({
            "origin": origin,
            "destination": destination,
            "date": day.isoformat() if day else None,
            "trips": [data.serialize_trip(t) for t in running],
            "other_days": [data.serialize_trip(t) for t in other_days],
        })

    @app.post("/api/bookings")
    def api_create_booking():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"errors": {"form": "Send the booking as JSON."}}), 400

        errors = {}
        trip = data.TRIPS_BY_ID.get(body.get("trip_id"))
        if trip is None:
            errors["trip_id"] = "That sailing no longer exists."

        fare = None
        if trip:
            fare = next((f for f in trip["fares"] if f["type"] == body.get("fare_class")), None)
            if fare is None:
                errors["fare_class"] = "Choose an accommodation for this sailing."

        travel_date = parse_date(body.get("date"))
        today = date.today()
        if travel_date is None:
            errors["date"] = "Choose a travel date."
        elif travel_date < today:
            errors["date"] = "That date has already passed."
        elif travel_date > today + timedelta(days=BOOKING_WINDOW_DAYS):
            errors["date"] = f"You can plan up to {BOOKING_WINDOW_DAYS} days ahead."
        elif trip and not data.runs_on(trip, travel_date):
            errors["date"] = f"This sailing runs {data.days_label(trip['days'])} only."

        try:
            passengers = int(body.get("passengers", 0))
            discounted = int(body.get("discounted", 0))
        except (TypeError, ValueError):
            passengers, discounted = 0, -1
        if not 1 <= passengers <= MAX_PASSENGERS:
            errors["passengers"] = f"Passengers must be between 1 and {MAX_PASSENGERS}."
        elif not 0 <= discounted <= passengers:
            errors["discounted"] = "Discounted passengers can't exceed the total."

        name = str(body.get("name") or "").strip()
        email = str(body.get("email") or "").strip()
        if not 2 <= len(name) <= 100:
            errors["name"] = "Enter the lead passenger's full name."
        if len(email) > 254 or not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."

        if errors:
            return jsonify({"errors": errors}), 400

        total = fare_total(fare["price"], passengers, discounted)
        db = get_db()
        for _ in range(5):
            reference = new_reference()
            try:
                db.execute(
                    "INSERT INTO bookings VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (reference, trip["id"], travel_date.isoformat(), fare["type"], passengers,
                     discounted, name, email, total, datetime.now().isoformat(timespec="seconds")))
                db.commit()
                break
            except sqlite3.IntegrityError:
                continue
        else:
            return jsonify({"errors": {"form": "Please try again."}}), 500

        return jsonify({"reference": reference, "total": total,
                        "url": url_for("booking_detail", reference=reference)}), 201

    @app.post("/api/waitlist")
    def api_waitlist():
        body = request.get_json(silent=True) or {}
        email = str(body.get("email") or "").strip().lower()
        if len(email) > 254 or not EMAIL_RE.match(email):
            return jsonify({"error": "Enter a valid email address."}), 400
        is_student = email.endswith(".edu.ph")
        db = get_db()
        db.execute("INSERT OR IGNORE INTO waitlist VALUES (?,?,?)",
                   (email, int(is_student), datetime.now().isoformat(timespec="seconds")))
        db.commit()
        return jsonify({"ok": True, "student": is_student})

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found."}), 404
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1",
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")))
