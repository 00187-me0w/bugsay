from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

FERRY_DATABASE = [
    {"id": 1, "company": "Lapu-Lapu Shipping", "type": "RORO", "route": "Hilongos-Baybay City", "departure": "06:00 AM", "arrival": "08:00 AM", "duration": "2 Hours", "price": 250, "status": "On Time"},
    {"id": 2, "company": "OceanJet", "type": "Fast Craft", "route": "Cebu City-Ormoc City", "departure": "08:00 AM", "arrival": "11:00 AM", "duration": "3 Hours", "price": 1200, "status": "On Time"},
    {"id": 3, "company": "Roble Shipping", "type": "RORO", "route": "Hilongos-Cebu City", "departure": "09:00 PM", "arrival": "03:00 AM", "duration": "6 Hours", "price": 850, "status": "Delayed"},
    {"id": 4, "company": "2GO Travel", "type": "Ferry", "route": "Ormoc City-Cebu City", "departure": "10:00 AM", "arrival": "02:00 PM", "duration": "4 Hours", "price": 950, "status": "On Time"},
    {"id": 5, "company": "OceanJet", "type": "Fast Craft", "route": "Cebu City-Ubay City", "departure": "06:00 AM", "arrival": "08:00 AM", "duration": "2 Hours", "price": 800, "status": "On Time"},
    {"id": 6, "company": "Lite Ferries", "type": "RORO", "route": "Ubay City-Cebu City", "departure": "12:00 PM", "arrival": "04:00 PM", "duration": "4 Hours", "price": 400, "status": "On Time"}
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