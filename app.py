"""Bugsay: ferry schedules, seat availability and bookings across Cebu, Leyte and Bohol."""

import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for

import data

MAX_PASSENGERS = 10
MAX_VEHICLES = 5
BOOKING_WINDOW_DAYS = 180
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PLATE_RE = re.compile(r"^[A-Z0-9][A-Z0-9 -]{1,11}$")
REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I

# Online methods are simulated in the prototype: nothing is charged and no
# payment details are collected.
PAYMENT_METHODS = {
    "gcash": {"label": "GCash", "icon": "fa-wallet", "online": True},
    "maya": {"label": "Maya", "icon": "fa-wallet", "online": True},
    "card": {"label": "Credit / debit card", "icon": "fa-credit-card", "online": True},
    "counter": {"label": "Pay at the terminal", "icon": "fa-building", "online": False},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    reference      TEXT PRIMARY KEY,
    trip_id        TEXT NOT NULL,
    travel_date    TEXT NOT NULL,
    fare_class     TEXT,
    email          TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    fare_total     INTEGER NOT NULL,
    discount_total INTEGER NOT NULL,
    vehicle_total  INTEGER NOT NULL,
    service_fee    INTEGER NOT NULL,
    total          INTEGER NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    reference      TEXT NOT NULL REFERENCES transactions(reference),
    seq            INTEGER NOT NULL,
    kind           TEXT NOT NULL CHECK (kind IN ('passenger', 'vehicle')),
    holder         TEXT NOT NULL,
    category       TEXT NOT NULL,
    accommodation  TEXT,
    cargo          TEXT,
    price          INTEGER NOT NULL,
    discount       INTEGER NOT NULL,
    fee            INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_sailing ON transactions (trip_id, travel_date);
CREATE INDEX IF NOT EXISTS idx_tickets_ref ON tickets (reference);
"""

NAV_ITEMS = [
    ("schedules", "Schedules"),
    ("availability", "Availability"),
    ("vehicle", "Vehicle booking"),
    ("route_map", "Port map"),
    ("updates", "Travel updates"),
    ("tourism", "Explore Visayas"),
]


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def new_reference():
    return "BG-" + "".join(secrets.choice(REF_ALPHABET) for _ in range(6))


def price_booking(trip, fare_class, passengers, vehicles):
    """Price a transaction. passengers: [{'type'}], vehicles: [{'type'}]."""
    fare = next((f for f in trip["fares"] if f["type"] == fare_class), None)
    rates = {v["type"]: v["price"] for v in trip["vehicles"]}
    lines = []
    for p in passengers:
        price = fare["price"]
        discounted = data.PASSENGER_TYPES[p["type"]]["discounted"]
        discount = price - data.discounted_price(price) if discounted else 0
        lines.append({"kind": "passenger", "price": price, "discount": discount,
                      "fee": data.SERVICE_FEE_PER_TICKET})
    for v in vehicles:
        lines.append({"kind": "vehicle", "price": rates[v["type"]], "discount": 0,
                      "fee": data.SERVICE_FEE_PER_VEHICLE})
    fare_total = sum(ln["price"] for ln in lines if ln["kind"] == "passenger")
    vehicle_total = sum(ln["price"] for ln in lines if ln["kind"] == "vehicle")
    discount_total = sum(ln["discount"] for ln in lines)
    service_fee = sum(ln["fee"] for ln in lines)
    return {"lines": lines, "fare_total": fare_total, "vehicle_total": vehicle_total,
            "discount_total": discount_total, "service_fee": service_fee,
            "total": fare_total + vehicle_total - discount_total + service_fee}


def booked_counts(db, travel_date, trip_ids=None):
    """{trip_id: {'seats': {class: n}, 'vehicles': {type: n}}} for one date."""
    sql = ("SELECT x.trip_id, t.kind, COALESCE(t.accommodation, t.category) AS bucket, COUNT(*) AS n "
           "FROM tickets t JOIN transactions x ON x.reference = t.reference "
           "WHERE x.travel_date = ?")
    args = [travel_date.isoformat()]
    if trip_ids is not None:
        sql += " AND x.trip_id IN (%s)" % ",".join("?" * len(trip_ids))
        args += list(trip_ids)
    sql += " GROUP BY x.trip_id, t.kind, bucket"
    counts = {}
    for row in db.execute(sql, args):
        entry = counts.setdefault(row["trip_id"], {"seats": {}, "vehicles": {}})
        entry["seats" if row["kind"] == "passenger" else "vehicles"][row["bucket"]] = row["n"]
    return counts


def availability_for(trip, travel_date, counts):
    """Seat and vehicle-slot availability for one sailing on one date."""
    taken = counts.get(trip["id"], {"seats": {}, "vehicles": {}})
    status = data.sailing_status(trip["id"], travel_date)
    seats = []
    for f in sorted(trip["fares"], key=lambda f: f["price"]):
        cap = data.seat_capacity(trip, f["type"])
        left = 0 if not status["bookable"] else max(cap - taken["seats"].get(f["type"], 0), 0)
        seats.append({"type": f["type"], "price": f["price"], "capacity": cap, "left": left})
    vehicles = []
    for v in trip["vehicles"]:
        cap = data.vehicle_capacity(trip, v["type"])
        left = 0 if not status["bookable"] else max(cap - taken["vehicles"].get(v["type"], 0), 0)
        vehicles.append({"type": v["type"], "price": v["price"], "capacity": cap, "left": left})
    return {"status": status, "seats": seats, "vehicles": vehicles,
            "demo": data.is_demo_inventory(trip),
            "seats_left": sum(s["left"] for s in seats),
            "seats_total": sum(s["capacity"] for s in seats)}


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
            g.db = sqlite3.connect(app.config["DATABASE"], isolation_level=None, timeout=10)
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
            "discount_pct": int(data.DISCOUNT_RATE * 100),
            "max_passengers": MAX_PASSENGERS,
            "max_vehicles": MAX_VEHICLES,
            "passenger_types": data.PASSENGER_TYPES,
            "vehicle_types": data.VEHICLE_TYPES,
            "vehicle_icons": data.VEHICLE_ICONS,
            "payment_methods": PAYMENT_METHODS,
            "fee_ticket": data.SERVICE_FEE_PER_TICKET,
            "fee_vehicle": data.SERVICE_FEE_PER_VEHICLE,
            "demo_seats": data.DEMO_SEATS_PER_CLASS,
            "demo_slots": data.DEMO_SLOTS_PER_VEHICLE_TYPE,
        }

    @app.template_filter("peso")
    def peso(value):
        return f"₱{value:,}"

    # ------------------------------------------------------------- pages

    @app.route("/")
    def home():
        featured = []
        for origin, dest in (("cebu", "baybay"), ("hilongos", "ubay"), ("cebu", "ormoc")):
            trips = data.trips_for_route(origin, dest)
            if trips:
                cheapest = min(trips, key=data.min_fare)
                featured.append({"key": f"{origin}-{dest}", "origin": origin, "destination": dest,
                                 "trip": data.serialize_trip(cheapest), "count": len(trips)})
        return render_template("index.html", featured=featured,
                               advisories=data.ADVISORIES[:2], routes=data.route_map())

    def schedules_page(mode):
        return render_template("schedules.html", mode=mode,
                               routes=data.route_map(vehicles_only=(mode == "vehicle")),
                               query=request.args)

    @app.route("/schedules")
    def schedules():
        return schedules_page("passenger")

    @app.route("/vehicle")
    def vehicle():
        return schedules_page("vehicle")

    @app.route("/availability")
    def availability():
        return render_template("availability.html", routes=data.route_map(), query=request.args)

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
        db = get_db()
        tx = db.execute("SELECT * FROM transactions WHERE reference = ?",
                        (reference.upper(),)).fetchone()
        if tx is None:
            return render_template("my_trip.html", not_found=reference), 404
        trip = data.TRIPS_BY_ID.get(tx["trip_id"])
        if trip is None:
            abort(404)
        tickets = db.execute("SELECT * FROM tickets WHERE reference = ? ORDER BY seq",
                             (tx["reference"],)).fetchall()
        return render_template(
            "booking.html", tx=tx, trip=data.serialize_trip(trip),
            travel_date=date.fromisoformat(tx["travel_date"]),
            passengers=[t for t in tickets if t["kind"] == "passenger"],
            vehicles=[t for t in tickets if t["kind"] == "vehicle"],
            payment=PAYMENT_METHODS[tx["payment_method"]])

    # --------------------------------------------------------------- API

    @app.get("/api/routes")
    def api_routes():
        return jsonify({"ports": data.PORTS, "routes": data.route_map(),
                        "vehicle_routes": data.route_map(vehicles_only=True)})

    @app.get("/api/trips")
    def api_trips():
        origin = request.args.get("origin", "")
        destination = request.args.get("destination", "")
        if origin not in data.PORTS or destination not in data.PORTS:
            return jsonify({"error": "Unknown port."}), 400
        if origin == destination:
            return jsonify({"error": "Origin and destination must be different."}), 400

        trips = data.trips_for_route(origin, destination)
        if request.args.get("mode") == "vehicle":
            trips = [t for t in trips if t["vehicles"]]
        day = parse_date(request.args.get("date"))
        if request.args.get("date") and day is None:
            return jsonify({"error": "Date must be YYYY-MM-DD."}), 400

        running = [t for t in trips if day is None or data.runs_on(t, day)]
        other_days = [t for t in trips if t not in running]
        counts = booked_counts(get_db(), day, [t["id"] for t in running]) if day and running else {}

        def with_availability(t):
            out = data.serialize_trip(t)
            if day:
                out["availability"] = availability_for(t, day, counts)
            return out

        return jsonify({
            "origin": origin,
            "destination": destination,
            "date": day.isoformat() if day else None,
            "trips": [with_availability(t) for t in running],
            "other_days": [data.serialize_trip(t) for t in other_days],
        })

    @app.get("/api/availability")
    def api_availability():
        day = parse_date(request.args.get("date")) or date.today()
        origin = request.args.get("origin") or None
        destination = request.args.get("destination") or None
        trips = [t for t in data.TRIPS if data.runs_on(t, day)
                 and (origin is None or t["origin"] == origin)
                 and (destination is None or t["destination"] == destination)]
        trips.sort(key=lambda t: (t["depart"], t["company"]))
        counts = booked_counts(get_db(), day, [t["id"] for t in trips]) if trips else {}
        sailings = []
        for t in trips:
            out = data.serialize_trip(t)
            out["availability"] = availability_for(t, day, counts)
            sailings.append(out)
        sailing_now = [s for s in sailings if s["availability"]["status"]["bookable"]]
        return jsonify({
            "date": day.isoformat(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "sailings": sailings,
            "totals": {  # seat totals only count sailings that are actually going
                "sailings": len(sailings),
                "seats_left": sum(s["availability"]["seats_left"] for s in sailing_now),
                "seats_total": sum(s["availability"]["seats_total"] for s in sailing_now),
                "cancelled": len(sailings) - len(sailing_now),
            },
        })

    def validate_booking(body):
        """Return (cleaned, errors)."""
        errors = {}
        trip = data.TRIPS_BY_ID.get(body.get("trip_id"))
        if trip is None:
            return None, {"trip_id": "That sailing no longer exists."}

        travel_date = parse_date(body.get("date"))
        today = date.today()
        if travel_date is None:
            errors["date"] = "Choose a travel date."
        elif travel_date < today:
            errors["date"] = "That date has already passed."
        elif travel_date > today + timedelta(days=BOOKING_WINDOW_DAYS):
            errors["date"] = f"You can book up to {BOOKING_WINDOW_DAYS} days ahead."
        elif not data.runs_on(trip, travel_date):
            errors["date"] = f"This sailing runs {data.days_label(trip['days'])} only."
        elif not data.sailing_status(trip["id"], travel_date)["bookable"]:
            errors["date"] = "This sailing is cancelled and can't be booked."

        passengers = body.get("passengers") or []
        if not isinstance(passengers, list) or len(passengers) > MAX_PASSENGERS:
            errors["passengers"] = f"Up to {MAX_PASSENGERS} passengers per booking."
            passengers = []
        clean_passengers = []
        for i, p in enumerate(passengers):
            p = p if isinstance(p, dict) else {}
            name = str(p.get("name") or "").strip()
            ptype = p.get("type", "regular")
            if not 2 <= len(name) <= 100:
                errors[f"passengers.{i}.name"] = f"Enter passenger {i + 1}'s full name."
            if ptype not in data.PASSENGER_TYPES:
                errors[f"passengers.{i}.type"] = "Choose a passenger type."
            clean_passengers.append({"name": name, "type": ptype})

        fare_class = body.get("fare_class")
        if clean_passengers and fare_class not in {f["type"] for f in trip["fares"]}:
            errors["fare_class"] = "Choose an accommodation."

        vehicles = body.get("vehicles") or []
        rates = {v["type"] for v in trip["vehicles"]}
        if not isinstance(vehicles, list) or len(vehicles) > MAX_VEHICLES:
            errors["vehicles"] = f"Up to {MAX_VEHICLES} vehicles per booking."
            vehicles = []
        if vehicles and not rates:
            errors["vehicles"] = "This sailing doesn't carry vehicles."
            vehicles = []
        clean_vehicles = []
        for i, v in enumerate(vehicles):
            v = v if isinstance(v, dict) else {}
            vtype = v.get("type")
            plate = re.sub(r"\s+", " ", str(v.get("plate") or "").strip().upper())
            cargo = str(v.get("cargo") or "").strip()[:120]
            if vtype not in rates:
                errors[f"vehicles.{i}.type"] = "This sailing doesn't take that vehicle type."
            if not PLATE_RE.match(plate):
                errors[f"vehicles.{i}.plate"] = f"Enter vehicle {i + 1}'s plate number."
            clean_vehicles.append({"type": vtype, "plate": plate, "cargo": cargo})

        if not clean_passengers and not clean_vehicles and "passengers" not in errors:
            errors["passengers"] = "Add at least one passenger or vehicle."

        email = str(body.get("email") or "").strip()
        if len(email) > 254 or not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
        payment_method = body.get("payment_method")
        if payment_method not in PAYMENT_METHODS:
            errors["payment_method"] = "Choose how you'll pay."

        return {"trip": trip, "date": travel_date, "fare_class": fare_class if clean_passengers else None,
                "passengers": clean_passengers, "vehicles": clean_vehicles,
                "email": email, "payment_method": payment_method}, errors

    def capacity_error(avail, b):
        if b["passengers"]:
            left = next(s["left"] for s in avail["seats"] if s["type"] == b["fare_class"])
            if left < len(b["passengers"]):
                if not left:
                    return {"fare_class": f"{b['fare_class']} is sold out."}
                return {"fare_class": f"Only {left} {b['fare_class']} seat{'s' if left != 1 else ''} left."}
        for vt in {v["type"] for v in b["vehicles"]}:
            wanted = sum(1 for v in b["vehicles"] if v["type"] == vt)
            left = next(v["left"] for v in avail["vehicles"] if v["type"] == vt)
            if left < wanted:
                return {"vehicles": f"Only {left} {vt} slot{'s' if left != 1 else ''} left."}
        return None

    @app.post("/api/bookings")
    def api_create_booking():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"errors": {"form": "Send the booking as JSON."}}), 400
        b, errors = validate_booking(body)
        if errors:
            return jsonify({"errors": errors}), 400

        trip, travel_date = b["trip"], b["date"]
        quote = price_booking(trip, b["fare_class"], b["passengers"], b["vehicles"])
        db = get_db()
        db.execute("BEGIN IMMEDIATE")  # lock so two people can't take the last seat
        try:
            avail = availability_for(trip, travel_date, booked_counts(db, travel_date, [trip["id"]]))
            problem = capacity_error(avail, b)
            if problem:
                db.execute("ROLLBACK")
                return jsonify({"errors": problem, "availability": avail}), 409

            reference = new_reference()
            while db.execute("SELECT 1 FROM transactions WHERE reference = ?", (reference,)).fetchone():
                reference = new_reference()
            db.execute(
                "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (reference, trip["id"], travel_date.isoformat(), b["fare_class"], b["email"],
                 b["payment_method"], quote["fare_total"], quote["discount_total"],
                 quote["vehicle_total"], quote["service_fee"], quote["total"],
                 datetime.now().isoformat(timespec="seconds")))
            rows = ([("passenger", p["name"], p["type"], b["fare_class"], None) for p in b["passengers"]]
                    + [("vehicle", v["plate"], v["type"], None, v["cargo"] or None) for v in b["vehicles"]])
            for seq, (row, line) in enumerate(zip(rows, quote["lines"]), start=1):
                db.execute("INSERT INTO tickets (reference, seq, kind, holder, category, accommodation, "
                           "cargo, price, discount, fee) VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (reference, seq, *row, line["price"], line["discount"], line["fee"]))
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise

        return jsonify({"reference": reference, "total": quote["total"], "tickets": len(rows),
                        "url": url_for("booking_detail", reference=reference)}), 201

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
