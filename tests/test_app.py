from datetime import date, timedelta

import pytest

import data
from app import create_app, fare_total


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})
    return app.test_client()


def next_weekday(weekday):
    """Next date (today or later) falling on the given weekday (Mon=0)."""
    d = date.today()
    return d + timedelta(days=(weekday - d.weekday()) % 7)


def booking_payload(**overrides):
    body = {
        "trip_id": "roble-ceb-hil-2100",  # daily
        "date": (date.today() + timedelta(days=1)).isoformat(),
        "fare_class": "Economy",
        "passengers": 2,
        "discounted": 1,
        "name": "Juan Dela Cruz",
        "email": "juan@example.com",
    }
    body.update(overrides)
    return body


# ------------------------------------------------------------------ pages

@pytest.mark.parametrize("path", [
    "/", "/schedules", "/updates", "/faq", "/map", "/rewards", "/tourism", "/privacy", "/my-trip",
    "/schedules?origin=cebu&destination=baybay&date=2030-01-01",
])
def test_pages_render(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert b"bugsay" in resp.data


def test_static_files_served(client):
    for path in ("/static/style.css", "/static/js/site.js", "/static/js/schedules.js",
                 "/static/favicon.svg"):
        assert client.get(path).status_code == 200, path


def test_unknown_page_is_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert b"drifted off" in resp.data


def test_no_card_fields_anywhere(client):
    """The old checkout asked for card numbers and CVVs. Make sure it stays gone."""
    page = client.get("/schedules").data.lower()
    assert b"cvv" not in page
    assert b"card number" not in page


# -------------------------------------------------------------------- data

def test_every_trip_uses_known_ports_and_unique_ids():
    ids = [t["id"] for t in data.TRIPS]
    assert len(ids) == len(set(ids))
    for t in data.TRIPS:
        assert t["origin"] in data.PORTS and t["destination"] in data.PORTS
        assert t["fares"] and t["days"]


def test_overnight_duration():
    trip = data.TRIPS_BY_ID["roble-ceb-hil-2100"]  # 21:00 -> 03:00
    assert data.duration_minutes(trip) == 6 * 60
    assert data.arrives_next_day(trip)
    assert data.format_time("21:00") == "9:00 PM"


def test_days_label():
    assert data.days_label(data.DAILY) == "Daily"
    assert data.days_label((data.MON, data.WED, data.FRI)) == "Mon, Wed, Fri"
    assert data.TRIPS_BY_ID["gabisan-ceb-hil-1400"]["days"] == (0, 2, 3, 4, 5, 6)
    assert data.days_label(data.TRIPS_BY_ID["gabisan-ceb-hil-1400"]["days"]) == "Daily except Tue"


def test_fare_total_applies_20_percent_discount():
    assert fare_total(500, 2, 0) == 1000
    assert fare_total(500, 2, 1) == 900
    assert fare_total(461, 1, 1) == 369  # round(368.8)


# --------------------------------------------------------------------- API

def test_search_returns_trips_with_display_fields(client):
    resp = client.get("/api/trips?origin=cebu&destination=ormoc")
    assert resp.status_code == 200
    trips = resp.get_json()["trips"]
    assert len(trips) == 4
    assert {"company", "depart_label", "duration_label", "min_fare", "fares"} <= trips[0].keys()
    assert [t["depart"] for t in trips] == sorted(t["depart"] for t in trips)


def test_search_filters_by_weekday(client):
    monday = next_weekday(data.MON).isoformat()
    body = client.get(f"/api/trips?origin=cebu&destination=baybay&date={monday}").get_json()
    assert [t["company"] for t in body["trips"]] == ["Roble Shipping"]  # Mon/Wed/Fri
    assert [t["company"] for t in body["other_days"]] == ["Lapu-Lapu Shipping"]  # Tue/Thu/Sun


def test_search_rejects_bad_input(client):
    assert client.get("/api/trips?origin=cebu&destination=mars").status_code == 400
    assert client.get("/api/trips?origin=cebu&destination=cebu").status_code == 400
    assert client.get("/api/trips?origin=cebu&destination=ormoc&date=tomorrow").status_code == 400


def test_routes_endpoint_lists_bato(client):
    routes = client.get("/api/routes").get_json()["routes"]
    assert routes["bato"] == ["ubay"]
    assert "ormoc" not in routes  # no departures from Ormoc are listed


def test_create_and_view_booking(client):
    resp = client.post("/api/bookings", json=booking_payload())
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["reference"].startswith("BG-")
    assert body["total"] == 461 + 369

    page = client.get(body["url"])
    assert page.status_code == 200
    assert body["reference"].encode() in page.data
    assert b"Juan Dela Cruz" in page.data
    assert b"This is not a ticket" in page.data


def test_lookup_redirects_and_handles_missing(client):
    ref = client.post("/api/bookings", json=booking_payload()).get_json()["reference"]
    resp = client.get(f"/my-trip?ref={ref[3:].lower()}")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/booking/{ref}")
    assert client.get("/booking/BG-NOPE00").status_code == 404


@pytest.mark.parametrize("overrides, field", [
    ({"trip_id": "nope"}, "trip_id"),
    ({"fare_class": "Penthouse"}, "fare_class"),
    ({"date": "2000-01-01"}, "date"),
    ({"date": (date.today() + timedelta(days=400)).isoformat()}, "date"),
    ({"passengers": 0}, "passengers"),
    ({"passengers": 11}, "passengers"),
    ({"passengers": 1, "discounted": 2}, "discounted"),
    ({"name": " "}, "name"),
    ({"email": "not-an-email"}, "email"),
])
def test_booking_validation(client, overrides, field):
    resp = client.post("/api/bookings", json=booking_payload(**overrides))
    assert resp.status_code == 400
    assert field in resp.get_json()["errors"]


def test_booking_rejects_day_the_trip_does_not_run(client):
    tuesday = next_weekday(data.TUE)
    if tuesday == date.today():
        tuesday += timedelta(days=7)
    resp = client.post("/api/bookings", json=booking_payload(
        trip_id="gabisan-ceb-hil-1400", fare_class="Tourist", date=tuesday.isoformat()))
    assert resp.status_code == 400
    assert "Daily except Tue" in resp.get_json()["errors"]["date"]


def test_booking_requires_json(client):
    assert client.post("/api/bookings", data="x").status_code == 400


def test_waitlist(client):
    resp = client.post("/api/waitlist", json={"email": "Ana@VSU.edu.ph"})
    assert resp.get_json() == {"ok": True, "student": True}
    # Signing up twice is fine.
    assert client.post("/api/waitlist", json={"email": "ana@vsu.edu.ph"}).status_code == 200
    assert client.post("/api/waitlist", json={"email": "nope"}).status_code == 400
