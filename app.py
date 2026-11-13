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

@app.route('/search', methods=['POST'])
def search_trips():
    data = request.json
    route_name = f"{data.get('origin')}-{data.get('destination')}"
    results = [trip for trip in FERRY_DATABASE if trip['route'] == route_name]
    return jsonify(results)

@app.route('/book', methods=['POST'])
def book_trip():
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
