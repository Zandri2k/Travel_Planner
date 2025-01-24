import streamlit as st
import pandas as pd
import folium
import osmnx as ox
import networkx as nx
import numpy as np
from utils.geo_utils import haversine, filter_stops_within_radius, calculate_midpoint, calculate_zoom_level
from backend.connect_to_api import ResRobot  # Assuming ResRobot is in backend/connect_to_api.py

# Initialize ResRobot
resrobot = ResRobot()

# Define city centers (latitude, longitude)
CITY_CENTERS = {
    "Stockholm": (59.3303, 18.0686),  # Stockholm Centralstation
    "Göteborg": (57.7089, 11.9735),   # Göteborg Centralstation
    "Malmö": (55.6096, 13.0007)       # Malmö Centralstation
}

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

# Function to interpolate points between route coordinates
def interpolate_points(route_coords, num_points=100):
    lats = np.array([coord[0] for coord in route_coords])
    lons = np.array([coord[1] for coord in route_coords])
    distances = np.cumsum(np.sqrt(np.ediff1d(lats, to_begin=0)**2 + np.ediff1d(lons, to_begin=0)**2))
    distances = distances / distances[-1]
    interpolated_lats = np.interp(np.linspace(0, 1, num_points), distances, lats)
    interpolated_lons = np.interp(np.linspace(0, 1, num_points), distances, lons)
    return list(zip(interpolated_lats, interpolated_lons))

# Streamlit UI
st.title("Public Transport Route Planner")
st.subheader("Plan Your Journey")

# Step 1: Let the user select a city (small selectbox in the corner)
selected_city = st.sidebar.selectbox("Välj stad", list(CITY_CENTERS.keys()))

# Get the city center coordinates
center_lat, center_lon = CITY_CENTERS[selected_city]

# Step 2: Filter stops within a 150km radius of the selected city
stops_within_radius = filter_stops_within_radius(stops_df, center_lat, center_lon, city_centers=CITY_CENTERS)

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

    # Fetch the next departure using the ResRobot API
    try:
        trip_details = resrobot.trips(origin_id=start_id, destination_id=end_id)
        
        if trip_details and "Trip" in trip_details and len(trip_details["Trip"]) > 0:
            next_departure = trip_details["Trip"][0]  # Take the first trip (next departure)
            st.subheader("Next Departure Details")
            st.json(next_departure)  # Display the next departure details in JSON format

            # Extract coordinates for the start and end points
            start_stop = stops_df[stops_df["stop_id"] == start_id].iloc[0]
            end_stop = stops_df[stops_df["stop_id"] == end_id].iloc[0]

            # Calculate midpoint and zoom level
            midpoint_lat, midpoint_lon = calculate_midpoint(
                start_stop["stop_lat"], start_stop["stop_lon"],
                end_stop["stop_lat"], end_stop["stop_lon"]
            )
            zoom_level = calculate_zoom_level(
                start_stop["stop_lat"], start_stop["stop_lon"],
                end_stop["stop_lat"], end_stop["stop_lon"]
            )

            # Create a Folium map centered at the midpoint
            m = folium.Map(location=[midpoint_lat, midpoint_lon], zoom_start=zoom_level)

            # Fetch the road network with higher resolution (no simplification)
            G = ox.graph_from_point((midpoint_lat, midpoint_lon), dist=20000, network_type="drive", simplify=False)

            # Initialize a list to store all route coordinates
            all_route_coords = []

            # Iterate through each leg of the trip
            for leg in next_departure["LegList"]["Leg"]:
                if "Stops" in leg and "Stop" in leg["Stops"]:
                    stops = leg["Stops"]["Stop"]
                    for i in range(len(stops) - 1):
                        # Get coordinates of current and next stop
                        current_stop = stops[i]
                        next_stop = stops[i + 1]

                        # Find the nearest nodes in the road network
                        start_node = ox.distance.nearest_nodes(G, current_stop["lon"], current_stop["lat"])
                        end_node = ox.distance.nearest_nodes(G, next_stop["lon"], next_stop["lat"])

                        # Find the shortest path between the two stops
                        route = nx.shortest_path(G, start_node, end_node, weight="length")

                        # Get the coordinates of the nodes in the route
                        route_coords = [(G.nodes[node]["y"], G.nodes[node]["x"]) for node in route]

                        # Interpolate points along the route for smoother curves
                        smoothed_route_coords = interpolate_points(route_coords, num_points=100)

                        # Add the smoothed route to the map
                        folium.PolyLine(
                            locations=smoothed_route_coords,
                            color="blue",
                            weight=5,  # Increase the weight to make the line thicker
                            opacity=1  # Ensure the opacity is set to 1 for full visibility
                        ).add_to(m)

                        # Add the coordinates to the list of all route coordinates
                        all_route_coords.extend(smoothed_route_coords)

            # Add markers for the start and end points
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

            # Add smaller markers for each stop along the route
            for leg in next_departure["LegList"]["Leg"]:
                if "Stops" in leg and "Stop" in leg["Stops"]:
                    for stop in leg["Stops"]["Stop"]:
                        folium.Marker(
                            location=[stop["lat"], stop["lon"]],
                            popup=f"{stop['name']}<br>{stop.get('arrTime', stop.get('depTime', 'N/A'))}",
                            icon=folium.Icon(color="blue", icon="circle", prefix="fa", icon_size=(10, 10))  # Smaller icon size
                        ).add_to(m)

            # Display the map in Streamlit
            folium_html = m._repr_html_()
            st.components.v1.html(folium_html, width=700, height=500)

        else:
            st.error("No departures found for the selected route. Please try again later.")

    except Exception as e:
        st.error(f"An error occurred while fetching trip details: {e}")

elif start_name or end_name:
    st.info("Please select both start and end points.")