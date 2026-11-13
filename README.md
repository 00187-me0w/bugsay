# bugsay

Ferry schedules for the Visayas. Bugsay lets you look up and compare sailings between
**Cebu, Leyte and Bohol**, see which ones run on your travel date, and save a trip plan
with an estimated fare to bring to the port.

> Bugsay is a prototype. Schedules and fares are reference values carried over from the
> original project and may be out of date. It does **not** sell tickets or take payments.

## Features

- **Schedule search** – pick ports, date and passengers; results only show sailings that run
  on that weekday, with crossing time, overnight arrivals (`+1`) and every fare class.
- **Round trips** – searches the return leg too, when return sailings exist.
- **Trip plans** – save a sailing with passenger details and get a reference (`BG-XXXXXX`).
  Fare estimates apply the 20% student / senior / PWD discount. Look plans up under *My trip*.
- **Port map** – Leaflet + OpenStreetMap map of every listed port and route.
- **Travel updates, FAQ, destinations, rewards waitlist, privacy policy.**

Routes currently listed: Cebu ⇄ Hilongos, Cebu ⇄ Baybay, Cebu → Ormoc, Hilongos → Ubay,
Bato → Ubay.

## Run it locally

Needs Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000. Set `FLASK_DEBUG=1` for auto-reload while developing.
Trip plans and waitlist sign-ups are stored in `instance/bugsay.sqlite3` (created automatically,
not committed).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
flake8 .
```

GitHub Actions runs both on every push and pull request.

## Project layout

```
app.py              Flask app: pages, JSON API, SQLite storage
data.py             Ports, sailings, advisories, destinations + helpers
templates/          Jinja templates (base.html holds the shared nav/footer)
static/style.css    Styles
static/js/          site.js (nav, search form), schedules.js (results, save-trip dialog)
tests/              pytest suite
```

## API

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/routes` | Ports and which destinations each one sails to |
| GET | `/api/trips?origin=cebu&destination=baybay&date=2026-12-01` | Sailings on that date, plus `other_days` for ones that don't run then |
| POST | `/api/bookings` | Save a trip plan. JSON: `trip_id, date, fare_class, passengers, discounted, name, email` |
| POST | `/api/waitlist` | Join the rewards waitlist. JSON: `email` |

## Updating schedules

Edit `TRIPS` in `data.py`. Each sailing has an `id`, `company`, `origin`/`destination`
(keys from `PORTS`), 24-hour `depart`/`arrive` times, the weekdays it runs
(`MON`…`SUN` or `DAILY`) and its fares. Run `pytest` afterwards.

## Photo credits

Destination photos are from Wikimedia Commons under Creative Commons licences; each card on
the *Explore Visayas* page links to its source and author. Hero images are from Unsplash.
