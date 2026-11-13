"""Static ferry data for Bugsay.

Carriers, times and fares are carried over from the original prototype.
They are reference values, not live availability: always confirm with the
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
             "coords": (10.3283, 124.7906)},
    "baybay": {"name": "Baybay City", "island": "Leyte", "terminal": "Baybay City Port",
               "coords": (10.6781, 124.7963)},
    "ormoc": {"name": "Ormoc City", "island": "Leyte", "terminal": "Ormoc City Pier",
              "coords": (11.0049, 124.6067)},
    "ubay": {"name": "Ubay", "island": "Bohol", "terminal": "Ubay Port",
             "coords": (10.0620, 124.4795)},
}


def _trip(trip_id, company, origin, destination, depart, arrive, days, fares,
          kind="Passenger ferry", vessel=None):
    return {
        "id": trip_id, "company": company, "vessel": vessel, "kind": kind,
        "origin": origin, "destination": destination,
        "depart": depart, "arrive": arrive, "days": tuple(days),
        "fares": [{"type": t, "price": p} for t, p in fares],
    }


TRIPS = [
    _trip("roble-ceb-hil-2100", "Roble Shipping", "cebu", "hilongos", "21:00", "03:00", DAILY,
          [("Economy", 461), ("Sitting", 516), ("Tourist", 816), ("Cabin", 1600)]),
    _trip("roble-hil-ceb-2200", "Roble Shipping", "hilongos", "cebu", "22:00", "04:00", DAILY,
          [("Economy", 461), ("Sitting", 516), ("Tourist", 816), ("Cabin", 1600)]),
    _trip("roble-ceb-bay-2100", "Roble Shipping", "cebu", "baybay", "21:00", "03:00", (MON, WED, FRI),
          [("Sitting", 540), ("Economy", 600), ("Deluxe", 780), ("Tourist", 840), ("Cabin", 1625)]),
    _trip("roble-bay-ceb-2100", "Roble Shipping", "baybay", "cebu", "21:00", "03:00", (TUE, THU, SUN),
          [("Sitting", 540), ("Economy", 600), ("Deluxe", 780), ("Tourist", 840), ("Cabin", 1625)]),
    _trip("roble-ceb-orm-2200", "Roble Shipping", "cebu", "ormoc", "22:00", "04:00", DAILY,
          [("Sitting", 660), ("Economy", 720), ("Tourist", 936), ("Cabin", 1965)]),
    _trip("gabisan-ceb-hil-1400", "Gabisan", "cebu", "hilongos", "14:00", "19:00",
          (MON, WED, THU, FRI, SAT, SUN),
          [("Economy B", 750), ("Economy A", 800), ("Tourist", 850)], vessel="MV Gloria 1"),
    _trip("gabisan-hil-ceb-2100", "Gabisan", "hilongos", "cebu", "21:00", "02:00", (MON, TUE, THU, SAT),
          [("Economy B", 500), ("Economy A", 520), ("Tourist", 680)], vessel="MV Gloria 2"),
    _trip("lapulapu-ceb-bay-2000", "Lapu-Lapu Shipping", "cebu", "baybay", "20:00", "02:00",
          (TUE, THU, SUN),
          [("Economy C", 450), ("Economy B", 510), ("Economy A", 520), ("Aircon", 640)]),
    _trip("lapulapu-bay-ceb-2000", "Lapu-Lapu Shipping", "baybay", "cebu", "20:00", "02:00",
          (MON, WED, FRI),
          [("Economy C", 450), ("Economy B", 510), ("Economy A", 520), ("Aircon", 640)]),
    _trip("lite-ceb-orm-1100", "Lite Ferries", "cebu", "ormoc", "11:00", "16:00", DAILY,
          [("Standard A/B", 812), ("Tourist", 1050), ("Business", 1604), ("Cabin", 2030)]),
    _trip("oceanjet-ceb-orm-0600", "OceanJet", "cebu", "ormoc", "06:00", "09:00", DAILY,
          [("Open Air / Business", 1320)], kind="Fast craft"),
    _trip("oceanjet-ceb-orm-1300", "OceanJet", "cebu", "ormoc", "13:00", "16:00", DAILY,
          [("Open Air / Business", 1320)], kind="Fast craft"),
    _trip("medallion-bat-uba-0800", "Medallion Transport", "bato", "ubay", "08:00", "11:00", DAILY,
          [("Economy", 580), ("Tourist", 630)]),
    _trip("leopards-hil-uba-1130", "Leopards Motorboat", "hilongos", "ubay", "11:30", "14:00", DAILY,
          [("Economy", 500), ("Business", 600)], kind="Motorboat"),
    _trip("penafrancia-hil-uba-1300", "Peñafrancia Corp", "hilongos", "ubay", "13:00", "15:30", DAILY,
          [("Regular", 510)]),
]

TRIPS_BY_ID = {t["id"]: t for t in TRIPS}

# Example advisories. These are illustrative, not real notices.
ADVISORIES = [
    {"date": date(2026, 11, 12), "level": "suspended", "label": "Coast Guard advisory",
     "title": "Weather can change a crossing.",
     "body": "Example: when a low-pressure area is near, fast craft trips from Cebu to Ormoc City "
             "can be suspended and larger vessels may sail late. Check your carrier's notice "
             "before leaving for the port."},
    {"date": date(2026, 11, 10), "level": "changed", "label": "Schedule adjustment",
     "title": "A different time. The same destination.",
     "body": "Departure times and boarding gates can change. Recheck your trip details and "
             "allow extra time at the terminal."},
    {"date": date(2026, 11, 8), "level": "normal", "label": "Normal operations",
     "title": "Back on schedule.",
     "body": "Example: after sea conditions settle, carriers such as Lapu-Lapu Shipping and "
             "Roble Shipping resume their standard schedules at Hilongos Port."},
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
    }


def trips_for_route(origin, destination):
    found = [t for t in TRIPS if t["origin"] == origin and t["destination"] == destination]
    return sorted(found, key=lambda t: t["depart"])


def route_map():
    """{origin_key: [destination_key, ...]} for every route that has sailings."""
    routes = {}
    for t in TRIPS:
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
