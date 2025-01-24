import streamlit as st
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from backend.connect_to_api import ResRobot  # Reuse your existing ResRobot class
from frontend.plot_maps import TripMap  # Reuse your existing TripMap class

# Initialize ResRobot
resrobot = ResRobot()

# Load stops.txt data locally
@st.cache_data
def load_stops(file_path="data/stops.txt"):
    """Load stop data from a local file."""
    columns = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"]
    df = pd.read_csv(file_path, names=columns, header=0)
    return df

# Load stops
stops_df = load_stops()
stop_dict = dict(zip(stops_df["stop_name"], stops_df["stop_id"]))

# Define city centers (latitude, longitude)
CITY_CENTERS = {
    "Stockholm": (59.3303, 18.0686),  # Stockholm Centralstation
    "Göteborg": (57.7089, 11.9735),   # Göteborg Centralstation
    "Malmö": (55.6096, 13.0007)       # Malmö Centralstation
}

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

# Function to filter stops within a 150km radius of a city center
def filter_stops_within_radius(stops_df, center_lat, center_lon, radius_km=150):
    """Filter stops within a given radius of a city center."""
    stops_within_radius = []
    for _, row in stops_df.iterrows():
        stop_lat = row["stop_lat"]
        stop_lon = row["stop_lon"]
        distance = haversine(center_lat, center_lon, stop_lat, stop_lon)
        if distance <= radius_km:
            stops_within_radius.append(row["stop_name"])
    return stops_within_radius

# Streamlit UI
st.title("Public Transport Route Planner")
st.subheader("Plan Your Journey")

# Step 1: Let the user select a city
selected_city = st.selectbox("Välj stad", list(CITY_CENTERS.keys()))

# Get the city center coordinates
center_lat, center_lon = CITY_CENTERS[selected_city]

# Step 2: Filter stops within a 150km radius of the selected city
stops_within_radius = filter_stops_within_radius(stops_df, center_lat, center_lon)

# Step 3: Selectbox for start and end points
start_name = st.selectbox("Start Point", stops_within_radius)
end_name = st.selectbox("End Point", stops_within_radius)

# Display selected stops
if start_name:
    st.write(f"Selected Start Point: **{start_name}**")
if end_name:
    st.write(f"Selected End Point: **{end_name}**")

# Fetch trip details when both points are selected
if start_name and end_name:
    st.write(f"Planning trip: **{start_name} → {end_name}**")

    # Get stop IDs
    start_id = stop_dict[start_name]
    end_id = stop_dict[end_name]

    # Call the ResRobot API (commented out for now)
    # trip_data = resrobot.trips(origin_id=start_id, destination_id=end_id)

    # if trip_data and "Trip" in trip_data:
    #     trip_segments = trip_data["Trip"][0]["Leg"]
    #     trip_stops = []

    #     for segment in trip_segments:
    #         if "Origin" in segment and "Destination" in segment:
    #             trip_stops.append({
    #                 "name": segment["Origin"]["name"],
    #                 "lat": segment["Origin"]["lat"],
    #                 "lon": segment["Origin"]["lon"],
    #                 "time": segment["Origin"]["time"]
    #             })
    #             trip_stops.append({
    #                 "name": segment["Destination"]["name"],
    #                 "lat": segment["Destination"]["lat"],
    #                 "lon": segment["Destination"]["lon"],
    #                 "time": segment["Destination"]["time"]
    #             })

    #     # Convert trip stops to a DataFrame
    #     stops_df = pd.DataFrame(trip_stops).drop_duplicates()

    #     # Pass the DataFrame to `TripMap` and display the map
    #     trip_map = TripMap(stops_df)
    #     trip_map.display_map()

    # else:
    #     st.error("No trip data available. Check API response.")
elif start_name or end_name:
    st.info("Please select both start and end points.")