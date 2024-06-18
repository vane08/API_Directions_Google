from flask import Flask, render_template, request, jsonify
import googlemaps
import numpy as np
from scipy.spatial.distance import cdist

app = Flask(__name__)

# Configura tu clave de API de Google Maps
gmaps = googlemaps.Client(key='AIzaSyAgIwoNsnI4JVgb-jGacBcRLiOd9JMLtRs')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_directions', methods=['POST'])
def get_directions():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    waypoints = data.get('waypoints', [])
    travel_mode = data.get('travel_mode')

    distances = gmaps.distance_matrix(
        [origin] + waypoints + [destination],
        [origin] + waypoints + [destination],
        mode=travel_mode.lower()
    )

    distance_matrix = np.zeros((len(waypoints) + 2, len(waypoints) + 2))

    for i, row in enumerate(distances['rows']):
        for j, element in enumerate(row['elements']):
            if element['status'] == 'OK':
                distance_matrix[i][j] = element['distance']['value']
            else:
                distance_matrix[i][j] = np.inf

    if waypoints:
        indices = list(range(1, len(waypoints) + 1))
        perm = np.argmin(cdist([distance_matrix[0]], distance_matrix[indices, :]), axis=1)
        optimized_waypoints = [origin] + [waypoints[i] for i in perm] + [destination]
    else:
        optimized_waypoints = [origin, destination]

    total_distance = np.sum([distance_matrix[i][i + 1] for i in range(len(optimized_waypoints) - 1)]) / 1000  # en kilómetros

    if travel_mode.lower() in ['walking', 'bicycling']:
        total_fuel_cost = 0
    else:
        total_fuel_cost = calculate_fuel_cost(total_distance)
    
    total_toll_cost = calculate_toll_cost(total_distance, travel_mode.lower())
    total_trip_cost = total_fuel_cost + total_toll_cost

    return jsonify({
        'origin': origin,
        'destination': destination,
        'waypoints': optimized_waypoints[1:-1] if waypoints else [],
        'total_distance': total_distance,
        'total_duration': calculate_duration(total_distance, travel_mode),
        'total_fuel_cost': total_fuel_cost,
        'total_toll_cost': total_toll_cost,
        'total_trip_cost': total_trip_cost
    })

@app.route('/get_toll_locations', methods=['POST'])
def get_toll_locations():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    waypoints = data.get('waypoints', [])

    total_distance = data.get('total_distance', 0)  # Obtener la distancia total del JSON de entrada

    if total_distance < 50:  # No cobrar peajes si la distancia es menor a 50 km
        return jsonify([])  # Retorna una lista vacía

    if data.get('travel_mode').lower() in ['walking', 'bicycling']:
        return jsonify([])  # Retorna una lista vacía si es a pie o en bicicleta

    all_points = [origin] + waypoints + [destination]

    toll_locations = []

    for point in all_points:
        places_result = gmaps.places_nearby(location=point, radius=5000, keyword='toll booth')
        if 'results' in places_result:
            toll_locations.extend([{'name': toll['name'], 'location': toll['geometry']['location']} for toll in places_result['results']])

    return jsonify(toll_locations)

def calculate_fuel_cost(distance_km, fuel_efficiency=10, fuel_price=20):
    fuel_cost = (distance_km / fuel_efficiency) * fuel_price
    return fuel_cost

def calculate_toll_cost(distance_km, travel_mode, cost_per_km=0.5):
    if travel_mode in ['walking', 'bicycling']:
        return 0
    if distance_km < 50:  # No cobrar peajes si la distancia es menor a 50 km
        return 0
    toll_cost = distance_km * cost_per_km
    return toll_cost

def calculate_duration(distance_km, travel_mode):
    speeds = {
        'driving': 60,
        'bicycling': 15,
        'walking': 5
    }
    speed = speeds.get(travel_mode.lower(), 60)
    duration_hours = distance_km / speed
    hours = int(duration_hours)
    minutes = int((duration_hours - hours) * 60)
    return f"{hours} horas y {minutes} minutos"

if __name__ == '__main__':
    app.run(debug=True)
