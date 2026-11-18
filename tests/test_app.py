from datetime import date, timedelta

import pytest

import data
from app import create_app, price_booking


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})
    return app.test_client()


def next_weekday(weekday, not_today=False):
    """Next date (today or later) falling on the given weekday (Mon=0)."""
    d = date.today()
    d += timedelta(days=(weekday - d.weekday()) % 7)
    if not_today and d == date.today():
        d += timedelta(days=7)
    return d


TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def booking(**overrides):
    body = {
        "trip_id": "roble-ceb-hil-2100",  # daily, carries motorcycles/cars/SUVs
        "date": TOMORROW,
        "fare_class": "Economy",
        "passengers": [{"name": "Juan Dela Cruz", "type": "regular"},
                       {"name": "Ana Reyes", "type": "student"}],
        "vehicles": [],
        "email": "juan@example.com",
        "payment_method": "gcash",
    }
    body.update(overrides)
    return body


def availability(client, trip_id="roble-ceb-hil-2100", day=TOMORROW):
    body = client.get(f"/api/availability?date={day}").get_json()
    return next(s for s in body["sailings"] if s["id"] == trip_id)["availability"]


# ------------------------------------------------------------------ pages

@pytest.mark.parametrize("path", [
    "/", "/schedules", "/vehicle", "/availability", "/updates", "/faq", "/map", "/tourism",
    "/privacy", "/my-trip", "/schedules?origin=cebu&destination=baybay&date=2030-01-01",
    "/vehicle?origin=cebu&destination=ormoc&vehicle_type=Car",
])
def test_pages_render(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert b"BUGSAY" in resp.data


def test_static_files_served(client):
    for path in ("/static/style.css", "/static/js/site.js", "/static/js/sheet.js",
                 "/static/js/schedules.js", "/static/js/availability.js", "/static/logo.png"):
        assert client.get(path).status_code == 200, path


def test_unknown_page_is_404(client):
    resp = client.get("/rewards")
    assert resp.status_code == 404
    assert b"drifted off" in resp.data


def test_no_payment_detail_fields(client):
    """Online payment is simulated; card numbers, CVVs and wallet numbers must never be asked for."""
    for path in ("/schedules", "/vehicle"):
        page = client.get(path).data.lower()
        assert b"cvv" not in page
        assert b"card number" not in page
        assert b'type="tel"' not in page


# -------------------------------------------------------------------- data

def test_every_trip_uses_known_ports_and_unique_ids():
    ids = [t["id"] for t in data.TRIPS]
    assert len(ids) == len(set(ids))
    for t in data.TRIPS:
        assert t["origin"] in data.PORTS and t["destination"] in data.PORTS
        assert t["fares"] and t["days"]
        assert all(v["type"] in data.VEHICLE_TYPES for v in t["vehicles"])


def test_fast_craft_carries_no_vehicles():
    assert not data.TRIPS_BY_ID["oceanjet-ceb-orm-0600"]["vehicles"]


def test_overnight_duration_and_labels():
    trip = data.TRIPS_BY_ID["roble-ceb-hil-2100"]
    assert data.duration_minutes(trip) == 6 * 60
    assert data.arrives_next_day(trip)
    assert data.format_time("21:00") == "9:00 PM"
    assert data.days_label(data.TRIPS_BY_ID["gabisan-ceb-hil-1400"]["days"]) == "Daily except Tue"


def test_pricing_discounts_passengers_not_vehicles():
    trip = data.TRIPS_BY_ID["roble-ceb-hil-2100"]
    q = price_booking(trip, "Economy",
                      [{"type": "regular"}, {"type": "student"}, {"type": "senior"}],
                      [{"type": "Car"}])
    assert q["fare_total"] == 461 * 3
    assert q["discount_total"] == 2 * (461 - 369)
    assert q["vehicle_total"] == 2000
    assert q["service_fee"] == 3 * 20 + 50
    assert q["total"] == 461 * 3 - 2 * 92 + 2000 + 110


# ------------------------------------------------------------------ search

def test_search_returns_availability(client):
    body = client.get(f"/api/trips?origin=cebu&destination=hilongos&date={TOMORROW}").get_json()
    trip = next(t for t in body["trips"] if t["id"] == "roble-ceb-hil-2100")
    seats = {s["type"]: s for s in trip["availability"]["seats"]}
    assert seats["Economy"] == {"type": "Economy", "price": 461, "capacity": 10, "left": 10}
    assert {v["type"] for v in trip["availability"]["vehicles"]} == {"Motorcycle", "Car", "SUV/Van"}


def test_search_filters_by_weekday(client):
    monday = next_weekday(data.MON).isoformat()
    body = client.get(f"/api/trips?origin=cebu&destination=baybay&date={monday}").get_json()
    assert [t["company"] for t in body["trips"]] == ["Roble Shipping"]
    assert [t["company"] for t in body["other_days"]] == ["Lapu-Lapu Shipping"]


def test_vehicle_mode_hides_sailings_without_vehicles(client):
    body = client.get(f"/api/trips?origin=cebu&destination=ormoc&date={TOMORROW}&mode=vehicle").get_json()
    assert {t["company"] for t in body["trips"]} == {"Roble Shipping", "Lite Ferries"}
    routes = client.get("/api/routes").get_json()["vehicle_routes"]
    assert "ubay" not in routes.get("hilongos", [])  # motorboats only on Hilongos-Ubay


def test_search_rejects_bad_input(client):
    assert client.get("/api/trips?origin=cebu&destination=mars").status_code == 400
    assert client.get("/api/trips?origin=cebu&destination=cebu").status_code == 400
    assert client.get("/api/trips?origin=cebu&destination=ormoc&date=tomorrow").status_code == 400


def test_cancelled_sailing_shows_and_has_no_seats(client):
    day = next_weekday(data.WED).isoformat()  # Gabisan MV Gloria 1 runs Wed but is suspended
    a = availability(client, "gabisan-ceb-hil-1400", day)
    assert a["status"]["status"] == "cancelled"
    assert a["seats_left"] == 0
    resp = client.post("/api/bookings", json=booking(trip_id="gabisan-ceb-hil-1400", date=day,
                                                     fare_class="Tourist"))
    assert resp.status_code == 400
    assert "cancelled" in resp.get_json()["errors"]["date"]


# ---------------------------------------------------------------- bookings

def test_multi_ticket_booking_and_ticket_page(client):
    resp = client.post("/api/bookings", json=booking(
        vehicles=[{"type": "Car", "plate": "abc 1234", "cargo": "Balikbayan boxes"}]))
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["tickets"] == 3
    assert body["total"] == 461 + 369 + 2000 + 2 * 20 + 50

    page = client.get(body["url"])
    assert page.status_code == 200
    for text in (body["reference"], "Juan Dela Cruz", "Ana Reyes", "ABC 1234", "Balikbayan boxes",
                 "Ticket 2 of 2", "-03", "Nothing was charged"):
        assert text.encode() in page.data, text


def test_vehicle_only_freight_booking(client):
    resp = client.post("/api/bookings", json=booking(
        trip_id="lapulapu-ceb-bay-2000", date=next_weekday(data.TUE).isoformat(), fare_class=None,
        passengers=[], vehicles=[{"type": "Truck", "plate": "LAB-9876", "cargo": "Copra"}],
        payment_method="counter"))
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["total"] == 4000 + 50


def test_booking_reduces_availability(client):
    client.post("/api/bookings", json=booking(
        vehicles=[{"type": "Motorcycle", "plate": "123ABC"}]))
    a = availability(client)
    seats = {s["type"]: s["left"] for s in a["seats"]}
    slots = {v["type"]: v["left"] for v in a["vehicles"]}
    assert seats["Economy"] == 8 and seats["Cabin"] == 10
    assert slots["Motorcycle"] == 9
    assert a["seats_left"] == a["seats_total"] - 2
    # A different day is unaffected.
    other = availability(client, day=(date.today() + timedelta(days=2)).isoformat())
    assert other["seats_left"] == other["seats_total"]


def test_cannot_overbook_a_class(client):
    ten = [{"name": f"Passenger {i}", "type": "regular"} for i in range(10)]
    assert client.post("/api/bookings", json=booking(passengers=ten)).status_code == 201
    resp = client.post("/api/bookings", json=booking(passengers=ten[:1]))
    assert resp.status_code == 409
    assert "sold out" in resp.get_json()["errors"]["fare_class"]
    assert resp.get_json()["availability"]["seats"][0]["left"] == 0


def test_cannot_overbook_vehicle_slots(client):
    for i in range(2):
        cars = [{"type": "Car", "plate": f"CAR{i}{j}00"} for j in range(5)]
        assert client.post("/api/bookings", json=booking(passengers=[], vehicles=cars)).status_code == 201
    extra = [{"type": "Car", "plate": "ZZZ999"}]
    resp = client.post("/api/bookings", json=booking(passengers=[], vehicles=extra))
    assert resp.status_code == 409
    assert "Car" in resp.get_json()["errors"]["vehicles"]


def test_lookup_redirects_and_handles_missing(client):
    ref = client.post("/api/bookings", json=booking()).get_json()["reference"]
    resp = client.get(f"/my-trip?ref={ref[3:].lower()}")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/booking/{ref}")
    assert client.get("/booking/BG-NOPE00").status_code == 404


@pytest.mark.parametrize("overrides, field", [
    ({"trip_id": "nope"}, "trip_id"),
    ({"fare_class": "Penthouse"}, "fare_class"),
    ({"date": "2000-01-01"}, "date"),
    ({"date": (date.today() + timedelta(days=400)).isoformat()}, "date"),
    ({"passengers": [], "vehicles": []}, "passengers"),
    ({"passengers": [{"name": "X", "type": "regular"}] * 11}, "passengers"),
    ({"passengers": [{"name": " ", "type": "regular"}]}, "passengers.0.name"),
    ({"passengers": [{"name": "Juan", "type": "vip"}]}, "passengers.0.type"),
    ({"vehicles": [{"type": "Bus", "plate": "ABC123"}]}, "vehicles.0.type"),
    ({"vehicles": [{"type": "Car", "plate": "!"}]}, "vehicles.0.plate"),
    ({"vehicles": [{"type": "Car", "plate": "A1"}] * 6}, "vehicles"),
    ({"email": "not-an-email"}, "email"),
    ({"payment_method": "bitcoin"}, "payment_method"),
])
def test_booking_validation(client, overrides, field):
    resp = client.post("/api/bookings", json=booking(**overrides))
    assert resp.status_code == 400
    assert field in resp.get_json()["errors"]


def test_vehicles_rejected_on_fast_craft(client):
    resp = client.post("/api/bookings", json=booking(
        trip_id="oceanjet-ceb-orm-0600", fare_class="Open Air / Business",
        vehicles=[{"type": "Car", "plate": "ABC123"}]))
    assert resp.status_code == 400
    assert "doesn't carry vehicles" in resp.get_json()["errors"]["vehicles"]


def test_booking_rejects_day_the_trip_does_not_run(client):
    tuesday = next_weekday(data.TUE, not_today=True)
    resp = client.post("/api/bookings", json=booking(
        trip_id="gabisan-ceb-hil-1400", fare_class="Tourist", date=tuesday.isoformat()))
    assert resp.status_code == 400
    assert "Daily except Tue" in resp.get_json()["errors"]["date"]


def test_booking_requires_json(client):
    assert client.post("/api/bookings", data="x").status_code == 400


def test_availability_dashboard_totals(client):
    body = client.get(f"/api/availability?date={TOMORROW}&origin=cebu&destination=ormoc").get_json()
    assert body["totals"]["sailings"] == len(body["sailings"]) == 4
    assert body["totals"]["seats_total"] == sum(s["availability"]["seats_total"] for s in body["sailings"])


def test_dashboard_totals_ignore_cancelled_sailings(client):
    day = next_weekday(data.WED).isoformat()
    body = client.get(f"/api/availability?date={day}&origin=cebu&destination=hilongos").get_json()
    assert body["totals"]["cancelled"] == 1
    assert body["totals"]["seats_total"] == 40  # only Roble's 4 classes x 10
