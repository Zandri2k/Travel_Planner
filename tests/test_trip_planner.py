import streamlit as st
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
import folium
from backend.connect_to_api import ResRobot  # Reuse your existing ResRobot class

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
            # Format the stop name as "Station Name, City"
            stop_name = row["stop_name"]
            city = next((city for city, coords in CITY_CENTERS.items() if haversine(center_lat, center_lon, coords[0], coords[1]) <= radius_km), "Unknown")
            formatted_name = f"{stop_name}, {city}"
            stops_within_radius.append(formatted_name)
    return stops_within_radius

# Streamlit UI
st.title("Public Transport Route Planner")
st.subheader("Plan Your Journey")

# Step 1: Let the user select a city (small selectbox in the corner)
selected_city = st.sidebar.selectbox("Välj stad", list(CITY_CENTERS.keys()))

# Get the city center coordinates
center_lat, center_lon = CITY_CENTERS[selected_city]

# Step 2: Filter stops within a 150km radius of the selected city
stops_within_radius = filter_stops_within_radius(stops_df, center_lat, center_lon)

# Step 3: Selectbox for start and end points (empty by default)
start_name = st.selectbox("Start Point", [""] + stops_within_radius)
end_name = st.selectbox("End Point", [""] + stops_within_radius)

# Display selected stops
if start_name:
    st.write(f"Selected Start Point: **{start_name}**")
if end_name:
    st.write(f"Selected End Point: **{end_name}**")

# Fetch trip details when both points are selected
if start_name and end_name:
    st.write(f"Planning trip: **{start_name} → {end_name}**")

    # Get stop IDs (remove the city part from the formatted name)
    start_id = stop_dict[start_name.split(", ")[0]]
    end_id = stop_dict[end_name.split(", ")[0]]

    # Fetch trip details using the ResRobot API
    trip_details = resrobot.trips(origin_id=start_id, destination_id=end_id)
    
    if trip_details:
        st.subheader("Trip Details")
        st.json(trip_details)  # Display trip details in JSON format

        # Extract coordinates for the start and end points
        start_stop = stops_df[stops_df["stop_id"] == start_id].iloc[0]
        end_stop = stops_df[stops_df["stop_id"] == end_id].iloc[0]

        # Create a Folium map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

        # Add markers for start and end points
        folium.Marker(
            location=[start_stop["stop_lat"], start_stop["stop_lon"]],
            popup=f"Start: {start_name}",
            icon=folium.Icon(color="green")
        ).add_to(m)

        folium.Marker(
            location=[end_stop["stop_lat"], end_stop["stop_lon"]],
            popup=f"End: {end_name}",
            icon=folium.Icon(color="red")
        ).add_to(m)

        # Display the map in Streamlit
        folium_html = m._repr_html_()
        st.components.v1.html(folium_html, width=700, height=500)

    else:
        st.error("Failed to fetch trip details. Please check the API connection or try again later.")

elif start_name or end_name:
    st.info("Please select both start and end points.")