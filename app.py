from datetime import date
from threading import Lock

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

FERRY_DATABASE = [
    {"company": "Roble Shipping", "route": "Cebu City-Hilongos", "departure": "09:00 PM", "arrival": "03:00 AM", "schedule_info": "Daily", "accommodations": [{"type": "Economy", "price": 461}, {"type": "Sitting", "price": 516}, {"type": "Tourist", "price": 816}, {"type": "Cabin", "price": 1600}]},
    {"company": "Roble Shipping", "route": "Hilongos-Cebu City", "departure": "10:00 PM", "arrival": "04:00 AM", "schedule_info": "Daily", "accommodations": [{"type": "Economy", "price": 461}, {"type": "Sitting", "price": 516}, {"type": "Tourist", "price": 816}, {"type": "Cabin", "price": 1600}]},
    {"company": "Roble Shipping", "route": "Cebu City-Baybay City", "departure": "09:00 PM", "arrival": "03:00 AM", "schedule_info": "Mon, Wed, Fri", "accommodations": [{"type": "Economy", "price": 600}, {"type": "Sitting", "price": 540}, {"type": "Deluxe", "price": 780}, {"type": "Tourist", "price": 840}, {"type": "Cabin", "price": 1625}]},
    {"company": "Roble Shipping", "route": "Baybay City-Cebu City", "departure": "09:00 PM", "arrival": "03:00 AM", "schedule_info": "Tue, Thu, Sun", "accommodations": [{"type": "Economy", "price": 600}, {"type": "Sitting", "price": 540}, {"type": "Deluxe", "price": 780}, {"type": "Tourist", "price": 840}, {"type": "Cabin", "price": 1625}]},
    {"company": "Roble Shipping", "route": "Cebu City-Ormoc City", "departure": "10:00 PM", "arrival": "04:00 AM", "schedule_info": "Daily", "accommodations": [{"type": "Economy", "price": 720}, {"type": "Sitting", "price": 660}, {"type": "Tourist", "price": 936}, {"type": "Cabin", "price": 1965}]},
    {"company": "Gabisan (MV Gloria 1)", "route": "Cebu City-Hilongos", "departure": "02:00 PM", "arrival": "07:00 PM", "schedule_info": "Daily (No Tuesday)", "accommodations": [{"type": "Economy B", "price": 750}, {"type": "Economy A", "price": 800}, {"type": "Tourist", "price": 850}]},
    {"company": "Gabisan (MV Gloria 2)", "route": "Hilongos-Cebu City", "departure": "09:00 PM", "arrival": "02:00 AM", "schedule_info": "Mon, Tue, Thu, Sat", "accommodations": [{"type": "Economy B", "price": 500}, {"type": "Economy A", "price": 520}, {"type": "Tourist", "price": 680}]},
    {"company": "Lapu-Lapu Shipping", "route": "Cebu City-Baybay City", "departure": "08:00 PM", "arrival": "02:00 AM", "schedule_info": "Tue, Thu, Sun", "accommodations": [{"type": "Economy C", "price": 450}, {"type": "Economy B", "price": 510}, {"type": "Economy A", "price": 520}, {"type": "Aircon", "price": 640}]},
    {"company": "Lapu-Lapu Shipping", "route": "Baybay City-Cebu City", "departure": "08:00 PM", "arrival": "02:00 AM", "schedule_info": "Mon, Wed, Fri", "accommodations": [{"type": "Economy C", "price": 450}, {"type": "Economy B", "price": 510}, {"type": "Economy A", "price": 520}, {"type": "Aircon", "price": 640}]},
    {"company": "Lite Ferries", "route": "Cebu City-Ormoc City", "departure": "11:00 AM", "arrival": "04:00 PM", "schedule_info": "Daily", "accommodations": [{"type": "Standard A/B", "price": 812}, {"type": "Tourist", "price": 1050}, {"type": "Business", "price": 1604}, {"type": "Cabin", "price": 2030}]},
    {"company": "OceanJet", "route": "Cebu City-Ormoc City", "departure": "06:00 AM", "arrival": "09:00 AM", "schedule_info": "Daily Fast Craft", "accommodations": [{"type": "Open Air / Bus.", "price": 1320}]},
    {"company": "OceanJet", "route": "Cebu City-Ormoc City", "departure": "01:00 PM", "arrival": "04:00 PM", "schedule_info": "Daily Fast Craft", "accommodations": [{"type": "Open Air / Bus.", "price": 1320}]},
    {"company": "Medallion Transport", "route": "Bato-Ubay", "departure": "08:00 AM", "arrival": "11:00 AM", "schedule_info": "Daily", "accommodations": [{"type": "Economy", "price": 580}, {"type": "Tourist", "price": 630}]},
    {"company": "Leopards Motorboat", "route": "Hilongos-Ubay", "departure": "11:30 AM", "arrival": "02:00 PM", "schedule_info": "Daily", "accommodations": [{"type": "Economy", "price": 500}, {"type": "Business", "price": 600}]},
    {"company": "Peñafrancia Corp", "route": "Hilongos-Ubay", "departure": "01:00 PM", "arrival": "03:30 PM", "schedule_info": "Daily", "accommodations": [{"type": "Regular", "price": 510}]}
]

# Manual counts override demo counts. Keys are (YYYY-MM-DD, company, route, departure).
# Example: ("2026-11-18", "Roble Shipping", "Cebu City-Hilongos", "09:00 PM"): {"Economy": 10}
FERRY_AVAILABILITY = {}
# Demo inventory is kept per date and sailing; replace it with real counts before production use.
DEMO_AVAILABILITY_PER_ACCOMMODATION = 10
DEMO_FERRY_AVAILABILITY = {}
# Override a sailing with "delayed" or "cancelled"; missing entries default to "scheduled".
# Use "*" as the date for advisories that remain in effect until further notice.
FERRY_STATUS = {
    ("*", "Gabisan (MV Gloria 1)", "Cebu City-Hilongos", "02:00 PM"): "cancelled"
}
FERRY_AVAILABILITY_LOCK = Lock()

def get_sailing_inventory(sailing_key, trip):
    with FERRY_AVAILABILITY_LOCK:
        if sailing_key in FERRY_AVAILABILITY:
            inventory = FERRY_AVAILABILITY[sailing_key]
            is_demo = False
        else:
            inventory = DEMO_FERRY_AVAILABILITY.setdefault(
                sailing_key,
                {
                    accommodation['type']: DEMO_AVAILABILITY_PER_ACCOMMODATION
                    for accommodation in trip['accommodations']
                }
            )
            is_demo = True

        if not isinstance(inventory, dict):
            return {}, is_demo
        return dict(inventory), is_demo

def get_sailing_status(sailing_key):
    wildcard_key = ('*', *sailing_key[1:])
    status = FERRY_STATUS.get(sailing_key, FERRY_STATUS.get(wildcard_key, 'scheduled'))
    return status if status in ('scheduled', 'delayed', 'cancelled') else 'unavailable'

VEHICLE_DATABASE = [
    # Cebu - Hilongos
    {"company": "Roble Shipping", "route": "Cebu City-Hilongos", "vehicle_type": "Motorcycle", "price": 800},
    {"company": "Roble Shipping", "route": "Cebu City-Hilongos", "vehicle_type": "Car", "price": 2000},
    {"company": "Roble Shipping", "route": "Cebu City-Hilongos", "vehicle_type": "SUV/Van", "price": 2800},
    {"company": "Gabisan (MV Gloria 1)", "route": "Cebu City-Hilongos", "vehicle_type": "Motorcycle", "price": 500},
    {"company": "Gabisan (MV Gloria 1)", "route": "Cebu City-Hilongos", "vehicle_type": "Car", "price": 1800},

    # Hilongos - Cebu
    {"company": "Roble Shipping", "route": "Hilongos-Cebu City", "vehicle_type": "Motorcycle", "price": 800},
    {"company": "Roble Shipping", "route": "Hilongos-Cebu City", "vehicle_type": "Car", "price": 2000},
    {"company": "Gabisan (MV Gloria 2)", "route": "Hilongos-Cebu City", "vehicle_type": "Motorcycle", "price": 500},

    # Cebu - Baybay
    {"company": "Roble Shipping", "route": "Cebu City-Baybay City", "vehicle_type": "Motorcycle", "price": 900},
    {"company": "Roble Shipping", "route": "Cebu City-Baybay City", "vehicle_type": "Car", "price": 2500},
    {"company": "Lapu-Lapu Shipping", "route": "Cebu City-Baybay City", "vehicle_type": "Motorcycle", "price": 850},
    {"company": "Lapu-Lapu Shipping", "route": "Cebu City-Baybay City", "vehicle_type": "Car", "price": 2400},
    {"company": "Lapu-Lapu Shipping", "route": "Cebu City-Baybay City", "vehicle_type": "Truck", "price": 4000},

    # Baybay - Cebu
    {"company": "Roble Shipping", "route": "Baybay City-Cebu City", "vehicle_type": "Car", "price": 2500},
    {"company": "Lapu-Lapu Shipping", "route": "Baybay City-Cebu City", "vehicle_type": "Truck", "price": 4000},

    # Cebu - Ormoc
    {"company": "Roble Shipping", "route": "Cebu City-Ormoc City", "vehicle_type": "Car", "price": 3000},
    {"company": "Lite Ferries", "route": "Cebu City-Ormoc City", "vehicle_type": "Motorcycle", "price": 1100},
    {"company": "Lite Ferries", "route": "Cebu City-Ormoc City", "vehicle_type": "Car", "price": 3200},
    {"company": "Lite Ferries", "route": "Cebu City-Ormoc City", "vehicle_type": "Bus", "price": 5000},

    # Bato / Ubay Routes
    {"company": "Medallion Transport", "route": "Bato-Ubay", "vehicle_type": "Motorcycle", "price": 600},
    {"company": "Medallion Transport", "route": "Bato-Ubay", "vehicle_type": "Car", "price": 2100}
]

@app.route('/')
def home(): return render_template('index.html')

@app.route('/schedules')
def schedules(): return render_template('schedules.html')

@app.route('/updates')
def updates(): return render_template('updates.html')

@app.route('/faq')
def faq(): return render_template('faq.html')

@app.route('/map')
def route_map(): return render_template('map.html')

@app.route('/rewards')
def rewards(): return render_template('rewards.html')

@app.route('/tourism')
def tourism(): return render_template('tourism.html')

@app.route('/privacy')
def privacy(): return render_template('privacy.html')

@app.route('/vehicle')
def vehicle(): return render_template('vehicle.html')

@app.route('/vehicle-search', methods=['POST'])
def search_vehicles():
    data = request.json
    route_name = f"{data.get('origin')}-{data.get('destination')}"
    vehicle_type = data.get('vehicle_type')
    
    results = [
        v for v in VEHICLE_DATABASE 
        if v['route'] == route_name and (not vehicle_type or vehicle_type == 'All' or v['vehicle_type'] == vehicle_type)
    ]
    return jsonify(results)

@app.route('/search', methods=['POST'])
def search_trips():
    data = request.get_json(silent=True) or {}
    route_name = f"{data.get('origin')}-{data.get('destination')}"
    sailing_date = data.get('date')
    try:
        date.fromisoformat(sailing_date)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "A valid sailing date is required."}), 400

    results = []
    for trip in FERRY_DATABASE:
        if trip['route'] != route_name:
            continue

        sailing_key = (sailing_date, trip['company'], trip['route'], trip['departure'])
        inventory, is_demo = get_sailing_inventory(sailing_key, trip)
        result = dict(trip)
        result['date'] = sailing_date
        result['status'] = get_sailing_status(sailing_key)
        result['demo_availability'] = is_demo
        result['accommodations'] = [
            {**accommodation, "available": inventory.get(accommodation['type'])}
            for accommodation in trip['accommodations']
        ]
        results.append(result)
    return jsonify(results)

@app.route('/book', methods=['POST'])
def book_trip():
    data = request.get_json(silent=True) or {}
    booking_type = data.get('booking_type')
    quantity = data.get('quantity', 1)
    student_quantity = data.get('student_quantity', 0)
    if type(quantity) is not int or quantity < 1:
        return jsonify({"status": "error", "message": "Quantity must be a positive whole number."}), 400
    if type(student_quantity) is not int or student_quantity < 0 or student_quantity > 1 or student_quantity > quantity:
        return jsonify({"status": "error", "message": "Only one student ticket is allowed per transaction."}), 400

    if booking_type == 'vehicle':
        return jsonify({"status": "success", "quantity": quantity, "student_quantity": student_quantity})
    if booking_type != 'ferry':
        return jsonify({"status": "error", "message": "Invalid booking type."}), 400

    sailing_date = data.get('date')
    try:
        date.fromisoformat(sailing_date)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "A valid sailing date is required."}), 400

    company = data.get('company')
    route = data.get('route')
    departure = data.get('departure')
    accommodation_type = data.get('accommodation')
    if not all(isinstance(value, str) for value in (company, route, departure, accommodation_type)):
        return jsonify({"status": "error", "message": "The selected sailing or accommodation is invalid."}), 400

    trip = next(
        (
            candidate for candidate in FERRY_DATABASE
            if candidate['company'] == company
            and candidate['route'] == route
            and candidate['departure'] == departure
        ),
        None
    )
    if trip is None or accommodation_type not in {
        accommodation['type'] for accommodation in trip['accommodations']
    }:
        return jsonify({"status": "error", "message": "The selected sailing or accommodation is invalid."}), 400

    sailing_key = (sailing_date, company, route, departure)
    with FERRY_AVAILABILITY_LOCK:
        status = get_sailing_status(sailing_key)
        if status != 'scheduled':
            return jsonify({"status": "error", "message": f"This sailing is {status} and cannot be booked."}), 409

        if sailing_key in FERRY_AVAILABILITY:
            inventory = FERRY_AVAILABILITY[sailing_key]
        else:
            inventory = DEMO_FERRY_AVAILABILITY.setdefault(
                sailing_key,
                {
                    accommodation['type']: DEMO_AVAILABILITY_PER_ACCOMMODATION
                    for accommodation in trip['accommodations']
                }
            )
        if not isinstance(inventory, dict) or type(inventory.get(accommodation_type)) is not int:
            return jsonify({"status": "error", "message": "Availability has not been entered for this accommodation."}), 409

        available = inventory[accommodation_type]
        if available < quantity:
            return jsonify({"status": "error", "message": "Not enough accommodation tickets are available."}), 409

        inventory[accommodation_type] = available - quantity

    return jsonify({
        "status": "success",
        "quantity": quantity,
        "student_quantity": student_quantity,
        "available": available - quantity,
        "demo_availability": sailing_key not in FERRY_AVAILABILITY
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
