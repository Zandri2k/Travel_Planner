from math import radians, sin, cos, sqrt, atan2

# Function to calculate distance using the Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points on the Earth's surface."""
    R = 6371  # Radius of the Earth in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Function to filter stops within a radius of a city center
def filter_stops_within_radius(stops_df, center_lat, center_lon, radius_km=150, city_centers=None):
    """Filter stops within a given radius of a city center."""
    stops_within_radius = []
    for _, row in stops_df.iterrows():
        stop_lat = row["stop_lat"]
        stop_lon = row["stop_lon"]
        distance = haversine(center_lat, center_lon, stop_lat, stop_lon)
        if distance <= radius_km:
            # Format the stop name as "Station Name, City"
            stop_name = row["stop_name"]
            city = "Unknown"
            if city_centers:
                city = next(
                    (city for city, coords in city_centers.items() 
                     if haversine(center_lat, center_lon, coords[0], coords[1]) <= radius_km),
                    "Unknown"
                )
            formatted_name = f"{stop_name}, {city}"
            stops_within_radius.append(formatted_name)
    return stops_within_radius

# Function to calculate the midpoint between two coordinates
def calculate_midpoint(lat1, lon1, lat2, lon2):
    """Calculate the midpoint between two latitude/longitude pairs."""
    return (lat1 + lat2) / 2, (lon1 + lon2) / 2

# Function to calculate the zoom level based on the distance between two points
def calculate_zoom_level(lat1, lon1, lat2, lon2):
    """Calculate an appropriate zoom level for the Folium map based on the distance between two points."""
    distance = haversine(lat1, lon1, lat2, lon2)
    if distance < 10:
        return 12
    elif distance < 50:
        return 10
    elif distance < 100:
        return 8
    else:
        return 6
    


