# bugsay

Your one-stop Visayas sea travel companion. Bugsay lets you compare sailings between
**Cebu, Leyte and Bohol**, see how many seats and vehicle slots are left, and book a whole
group plus their vehicles in one transaction.

> Bugsay is a prototype. Schedules, fares and vehicle rates are reference values from the
> project team, seat counts are demo inventory, and online payment is **simulated**: nothing
> is charged and no card or e-wallet details are collected.

## Features

- **Schedule search** – ports, date, passengers; only sailings that run that weekday, with
  crossing time, overnight arrivals (`+1`), sailing status and seats left per class.
- **Multiple tickets per transaction** – up to 10 passengers (each with their own name and
  fare type: regular, student, senior citizen, PWD) and up to 5 vehicles under one
  reference (`BG-XXXXXX`). Every passenger and vehicle gets its own ticket number
  (`BG-XXXXXX-01`, `-02`, …).
- **Availability dashboard** (`/availability`) – every sailing on a day with seats left per
  accommodation class and deck slots per vehicle type, cancelled sailings, fill rate.
  Refreshes every 30 seconds.
- **Vehicle / freight booking** (`/vehicle`) – RoRo rates for motorcycles, cars, SUVs/vans,
  trucks and buses, with plate number and optional cargo description. Vehicle-only
  (freight) bookings are allowed.
- **Pricing** – 20% off passenger fares for students, seniors and PWD (not vehicles), plus
  Bugsay's service fee of ₱20 per passenger ticket and ₱50 per vehicle.
- **Sailing status** – mark a sailing delayed or cancelled (per date or until further
  notice) in `SAILING_STATUS`; cancelled sailings can't be booked.
- **Port map, travel updates, FAQ, destinations, ad placeholders, privacy policy.**
- Apple-style UI: system font, translucent nav, bottom sheet with drag-to-dismiss on phones,
  light/dark mode, and support for reduced motion / transparency / higher contrast.

## Seat and vehicle capacity

Until carriers provide real numbers, every accommodation class has `DEMO_SEATS_PER_CLASS`
(10) seats and every vehicle type `DEMO_SLOTS_PER_VEHICLE_TYPE` (10) slots, per sailing per
day. Real capacities go in `SEAT_CAPACITY` / `VEHICLE_CAPACITY` in `data.py`. Seats left =
capacity − tickets already booked for that sailing and date, counted from the database, so
they survive restarts. Bookings lock the database while checking, so two people can't take
the last seat.

## Run it locally

Needs Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000. Set `FLASK_DEBUG=1` for auto-reload while developing.
Bookings are stored in `instance/bugsay.sqlite3` (created automatically, not committed).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
flake8 .
```

GitHub Actions runs both on every push and pull request.

## Project layout

```
app.py              Flask app: pages, JSON API, pricing, availability, SQLite storage
data.py             Ports, sailings, vehicle rates, capacity, status, advisories + helpers
templates/          Jinja templates (base.html holds the shared nav/footer)
static/style.css    Design system (tokens, light/dark, components)
static/js/          site.js (helpers, nav, search form), sheet.js (bottom sheet + springs),
                    schedules.js (results, booking sheet), availability.js (dashboard)
static/logo.png     Logo (also used as the map pin)
tests/              pytest suite
```

## API

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/routes` | Ports, routes, and routes that carry vehicles |
| GET | `/api/trips?origin=cebu&destination=baybay&date=2026-12-01[&mode=vehicle]` | Sailings that day with status and availability, plus `other_days` |
| GET | `/api/availability?date=2026-12-01[&origin=…&destination=…]` | Dashboard data: every sailing that day with availability and totals |
| POST | `/api/bookings` | Create a booking. JSON: `trip_id, date, fare_class, passengers[{name,type}], vehicles[{type,plate,cargo}], email, payment_method` |

`payment_method` is one of `gcash`, `maya`, `card`, `counter`. Returns `201` with the
reference, `400` with field errors, or `409` with fresh availability if seats ran out.

## Updating schedules

Edit `TRIPS` in `data.py`. Each sailing has an `id`, `company`, `origin`/`destination`
(keys from `PORTS`), 24-hour `depart`/`arrive` times, the weekdays it runs
(`MON`…`SUN` or `DAILY`), its fares and its vehicle rates. Run `pytest` afterwards.

## Photo credits

Destination photos are from Wikimedia Commons under Creative Commons licences; each card on
the *Explore Visayas* page links to its source and author. The hero image is from Pexels.
