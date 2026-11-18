"""Static ferry data for Bugsay.

Carriers, times, fares and vehicle rates come from the project team. They are
reference values, not live data from the carriers: always confirm with the
carrier before travelling.
"""

from datetime import date, datetime

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)
DAILY = (MON, TUE, WED, THU, FRI, SAT, SUN)
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# key -> port details. Coordinates are approximate pier locations.
PORTS = {
    "cebu": {"name": "Cebu City", "island": "Cebu", "terminal": "Cebu City Pier 3",
             "coords": (10.2917, 123.9062)},
    "hilongos": {"name": "Hilongos", "island": "Leyte", "terminal": "Hilongos Port",
                 "coords": (10.3735, 124.7482)},
    "bato": {"name": "Bato", "island": "Leyte", "terminal": "Bato Port",
             "coords": (10.3297, 124.7967)},
    "baybay": {"name": "Baybay City", "island": "Leyte", "terminal": "Baybay City Port",
               "coords": (10.6781, 124.7963)},
    "ormoc": {"name": "Ormoc City", "island": "Leyte", "terminal": "Ormoc City Pier",
              "coords": (11.0049, 124.6067)},
    "ubay": {"name": "Ubay", "island": "Bohol", "terminal": "Ubay Port",
             "coords": (10.0556, 124.4756)},
    "tagbilaran": {"name": "Tagbilaran City", "island": "Bohol", "terminal": "Tagbilaran Port",
                   "coords": (9.6457, 123.8540)},
}

# ---------------------------------------------------------------- pricing

# Philippine law gives students (RA 11314), senior citizens (RA 9994) and persons
# with disability (RA 10754) 20% off passenger fares. The carrier checks ID.
DISCOUNT_RATE = 0.20
PASSENGER_TYPES = {
    "regular": {"label": "Regular", "discounted": False},
    "student": {"label": "Student", "discounted": True},
    "senior": {"label": "Senior citizen", "discounted": True},
    "pwd": {"label": "PWD", "discounted": True},
}

# Bugsay's own platform fee, added on top of the carrier fare.
SERVICE_FEE_PER_TICKET = 20
SERVICE_FEE_PER_VEHICLE = 50

VEHICLE_TYPES = ("Motorcycle", "Car", "SUV/Van", "Truck", "Bus")
VEHICLE_ICONS = {"Motorcycle": "fa-motorcycle", "Car": "fa-car-side", "SUV/Van": "fa-van-shuttle",
                 "Truck": "fa-truck", "Bus": "fa-bus"}

# ------------------------------------------------------------ availability

# Demo inventory: every accommodation class has this many seats and every
# vehicle type this many deck slots per sailing per day, until real numbers
# from the carriers are entered in SEAT_CAPACITY / VEHICLE_CAPACITY.
DEMO_SEATS_PER_CLASS = 10
DEMO_SLOTS_PER_VEHICLE_TYPE = 10
SEAT_CAPACITY = {}      # {trip_id: {"Economy": 120, ...}}
VEHICLE_CAPACITY = {}   # {trip_id: {"Car": 20, ...}}

# Sailing status overrides: (date or "*", trip_id) -> status. Missing = scheduled.
# "*" means until further notice.
SAILING_STATUS = {
    ("*", "gabisan-ceb-hil-1400"): {
        "status": "cancelled",
        "note": "Suspended until further notice due to a low-pressure area.",
    },
}
STATUS_LABELS = {"scheduled": "On schedule", "delayed": "Delayed", "cancelled": "Cancelled"}


def _trip(trip_id, company, origin, destination, depart, arrive, days, fares,
          kind="Passenger ferry", vessel=None, vehicles=()):
    return {
        "id": trip_id, "company": company, "vessel": vessel, "kind": kind,
        "origin": origin, "destination": destination,
        "depart": depart, "arrive": arrive, "days": tuple(days),
        "fares": [{"type": t, "price": p} for t, p in fares],
        "vehicles": [{"type": t, "price": p} for t, p in vehicles],
    }


TRIPS = [
    _trip("roble-ceb-hil-2100", "Roble Shipping", "cebu", "hilongos", "21:00", "03:00", DAILY,
          [("Economy", 461), ("Sitting", 516), ("Tourist", 816), ("Cabin", 1600)],
          vehicles=[("Motorcycle", 800), ("Car", 2000), ("SUV/Van", 2800)]),
    _trip("roble-hil-ceb-2200", "Roble Shipping", "hilongos", "cebu", "22:00", "04:00", DAILY,
          [("Economy", 461), ("Sitting", 516), ("Tourist", 816), ("Cabin", 1600)],
          vehicles=[("Motorcycle", 800), ("Car", 2000)]),
    _trip("roble-ceb-bay-2100", "Roble Shipping", "cebu", "baybay", "21:00", "03:00", (MON, WED, FRI),
          [("Sitting", 540), ("Economy", 600), ("Deluxe", 780), ("Tourist", 840), ("Cabin", 1625)],
          vehicles=[("Motorcycle", 900), ("Car", 2500)]),
    _trip("roble-bay-ceb-2100", "Roble Shipping", "baybay", "cebu", "21:00", "03:00", (TUE, THU, SUN),
          [("Sitting", 540), ("Economy", 600), ("Deluxe", 780), ("Tourist", 840), ("Cabin", 1625)],
          vehicles=[("Car", 2500)]),
    _trip("roble-ceb-orm-2200", "Roble Shipping", "cebu", "ormoc", "22:00", "04:00", DAILY,
          [("Sitting", 660), ("Economy", 720), ("Tourist", 936), ("Cabin", 1965)],
          vehicles=[("Car", 3000)]),
    _trip("gabisan-ceb-hil-1400", "Gabisan", "cebu", "hilongos", "14:00", "19:00",
          (MON, WED, THU, FRI, SAT, SUN),
          [("Economy B", 750), ("Economy A", 800), ("Tourist", 850)], vessel="MV Gloria 1",
          vehicles=[("Motorcycle", 500), ("Car", 1800)]),
    _trip("gabisan-hil-ceb-2100", "Gabisan", "hilongos", "cebu", "21:00", "02:00", (MON, TUE, THU, SAT),
          [("Economy B", 500), ("Economy A", 520), ("Tourist", 680)], vessel="MV Gloria 2",
          vehicles=[("Motorcycle", 500)]),
    _trip("lapulapu-ceb-bay-2000", "Lapu-Lapu Shipping", "cebu", "baybay", "20:00", "02:00",
          (TUE, THU, SUN),
          [("Economy C", 450), ("Economy B", 510), ("Economy A", 520), ("Aircon", 640)],
          vehicles=[("Motorcycle", 850), ("Car", 2400), ("Truck", 4000)]),
    _trip("lapulapu-bay-ceb-2000", "Lapu-Lapu Shipping", "baybay", "cebu", "20:00", "02:00",
          (MON, WED, FRI),
          [("Economy C", 450), ("Economy B", 510), ("Economy A", 520), ("Aircon", 640)],
          vehicles=[("Truck", 4000)]),
    _trip("lite-ceb-orm-1100", "Lite Ferries", "cebu", "ormoc", "11:00", "16:00", DAILY,
          [("Standard A/B", 812), ("Tourist", 1050), ("Business", 1604), ("Cabin", 2030)],
          vehicles=[("Motorcycle", 1100), ("Car", 3200), ("Bus", 5000)]),
    _trip("oceanjet-ceb-orm-0600", "OceanJet", "cebu", "ormoc", "06:00", "09:00", DAILY,
          [("Open Air / Business", 1320)], kind="Fast craft"),
    _trip("oceanjet-ceb-orm-1300", "OceanJet", "cebu", "ormoc", "13:00", "16:00", DAILY,
          [("Open Air / Business", 1320)], kind="Fast craft"),
    _trip("medallion-bat-uba-0800", "Medallion Transport", "bato", "ubay", "08:00", "11:00", DAILY,
          [("Economy", 580), ("Tourist", 630)],
          vehicles=[("Motorcycle", 600), ("Car", 2100)]),
    _trip("leopards-hil-uba-1130", "Leopards Motorboat", "hilongos", "ubay", "11:30", "14:00", DAILY,
          [("Economy", 500), ("Business", 600)], kind="Motorboat"),
    _trip("penafrancia-hil-uba-1300", "Peñafrancia Corp", "hilongos", "ubay", "13:00", "15:30", DAILY,
          [("Regular", 510)]),
]

TRIPS_BY_ID = {t["id"]: t for t in TRIPS}

# Sample advisories (illustrative content for the prototype).
ADVISORIES = [
    {"date": date(2026, 11, 17), "level": "suspended", "label": "Coast Guard advisory",
     "title": "MV Gloria 1 update",
     "body": "Due to a low-pressure area, MV Gloria 1 from Cebu to Hilongos is temporarily "
             "suspended until further notice. RoRo vessels are operating on a delayed schedule."},
    {"date": date(2026, 11, 16), "level": "normal", "label": "Normal operations",
     "title": "Tide levels stabilized.",
     "body": "Lite Ferries and Roble Shipping have resumed their standard daily schedules."},
    {"date": date(2026, 11, 10), "level": "changed", "label": "Schedule adjustment",
     "title": "A different time. The same destination.",
     "body": "Departure times and boarding gates can change. Recheck your trip details and "
             "allow extra time at the terminal."},
]

DESTINATIONS = [
    {"name": "Cuatro Islas", "island": "Leyte", "port": "hilongos",
     "blurb": "Four small islands off Inopacan with white coral beaches. Sail into Hilongos, "
              "then head north along the coast for the island-hopping boats.",
     "image": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/cf/Digyo_Island.jpg/"
              "960px-Digyo_Island.jpg",
     "credit": "Warrendering", "license": "CC BY-SA 4.0",
     "source": "https://commons.wikimedia.org/wiki/File:Digyo_Island.jpg"},
    {"name": "Kalanggaman Island", "island": "Leyte", "port": "ormoc",
     "blurb": "A long sandbar off Palompon. Sail into Ormoc City, travel west by road to "
              "Palompon, then take a boat across.",
     "image": "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ef/Kalanggaman_Island_2024.jpg/"
              "960px-Kalanggaman_Island_2024.jpg",
     "credit": "Gcabig2024", "license": "CC BY-SA 4.0",
     "source": "https://commons.wikimedia.org/wiki/File:Kalanggaman_Island_2024.jpg"},
    {"name": "Lake Danao", "island": "Leyte", "port": "ormoc",
     "blurb": "A guitar-shaped mountain lake in the hills above Ormoc City. Good for a cool "
              "day trip after an early fast craft.",
     "image": "https://upload.wikimedia.org/wikipedia/commons/f/fd/Lake_Danao_Leyte.jpg",
     "credit": "Donnahday", "license": "CC BY-SA 4.0",
     "source": "https://commons.wikimedia.org/wiki/File:Lake_Danao_Leyte.jpg"},
    {"name": "Chocolate Hills", "island": "Bohol", "port": "ubay",
     "blurb": "Bohol's famous rolling hills in Carmen. Ubay is your sea gateway from Leyte; "
              "the hills are inland by road.",
     "image": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/28/Chocolate_Hills_overview.JPG/"
              "960px-Chocolate_Hills_overview.JPG",
     "credit": "P199", "license": "CC BY-SA 3.0",
     "source": "https://commons.wikimedia.org/wiki/File:Chocolate_Hills_overview.JPG"},
]


# ---------------------------------------------------------------- helpers

def _minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def duration_minutes(trip):
    """Crossing time in minutes. Arrivals earlier than departure are next day."""
    mins = _minutes(trip["arrive"]) - _minutes(trip["depart"])
    return mins + 24 * 60 if mins <= 0 else mins


def arrives_next_day(trip):
    return _minutes(trip["arrive"]) <= _minutes(trip["depart"])


def format_duration(mins):
    return f"{mins // 60}h {mins % 60:02d}m"


def format_time(hhmm):
    """'21:00' -> '9:00 PM'."""
    return datetime.strptime(hhmm, "%H:%M").strftime("%I:%M %p").lstrip("0")


def days_label(days):
    days = set(days)
    if days == set(DAILY):
        return "Daily"
    missing = set(DAILY) - days
    if len(missing) == 1:
        return f"Daily except {DAY_NAMES[missing.pop()]}"
    return ", ".join(DAY_NAMES[d] for d in sorted(days))


def min_fare(trip):
    return min(f["price"] for f in trip["fares"])


def runs_on(trip, day):
    return day.weekday() in trip["days"]


def discounted_price(price):
    return round(price * (1 - DISCOUNT_RATE))


def sailing_status(trip_id, day=None):
    """{'status': ..., 'label': ..., 'note': ...} for a sailing on a date."""
    entry = None
    if day is not None:
        entry = SAILING_STATUS.get((day.isoformat(), trip_id))
    entry = entry or SAILING_STATUS.get(("*", trip_id)) or {"status": "scheduled"}
    status = entry["status"]
    return {"status": status, "label": STATUS_LABELS.get(status, status.title()),
            "note": entry.get("note"), "bookable": status != "cancelled"}


def seat_capacity(trip, fare_type):
    return SEAT_CAPACITY.get(trip["id"], {}).get(fare_type, DEMO_SEATS_PER_CLASS)


def vehicle_capacity(trip, vehicle_type):
    return VEHICLE_CAPACITY.get(trip["id"], {}).get(vehicle_type, DEMO_SLOTS_PER_VEHICLE_TYPE)


def is_demo_inventory(trip):
    return trip["id"] not in SEAT_CAPACITY


def serialize_trip(trip):
    """Trip as JSON-friendly dict with display fields filled in."""
    mins = duration_minutes(trip)
    return {
        "id": trip["id"],
        "company": trip["company"],
        "vessel": trip["vessel"],
        "kind": trip["kind"],
        "origin": trip["origin"],
        "origin_name": PORTS[trip["origin"]]["name"],
        "destination": trip["destination"],
        "destination_name": PORTS[trip["destination"]]["name"],
        "depart": trip["depart"],
        "arrive": trip["arrive"],
        "depart_label": format_time(trip["depart"]),
        "arrive_label": format_time(trip["arrive"]),
        "next_day": arrives_next_day(trip),
        "duration_minutes": mins,
        "duration_label": format_duration(mins),
        "days": list(trip["days"]),
        "days_label": days_label(trip["days"]),
        "fares": sorted(trip["fares"], key=lambda f: f["price"]),
        "min_fare": min_fare(trip),
        "vehicles": trip["vehicles"],
        "carries_vehicles": bool(trip["vehicles"]),
    }


def trips_for_route(origin, destination):
    found = [t for t in TRIPS if t["origin"] == origin and t["destination"] == destination]
    return sorted(found, key=lambda t: t["depart"])


def route_map(vehicles_only=False):
    """{origin_key: [destination_key, ...]} for every route that has sailings."""
    routes = {}
    for t in TRIPS:
        if vehicles_only and not t["vehicles"]:
            continue
        dests = routes.setdefault(t["origin"], [])
        if t["destination"] not in dests:
            dests.append(t["destination"])
    return routes


def route_lines():
    """Unique port pairs with the carriers serving them, for the map."""
    lines = {}
    for t in TRIPS:
        pair = tuple(sorted((t["origin"], t["destination"])))
        entry = lines.setdefault(pair, {"ports": list(pair), "carriers": []})
        if t["company"] not in entry["carriers"]:
            entry["carriers"].append(t["company"])
    return list(lines.values())
