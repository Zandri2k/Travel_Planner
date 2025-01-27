import streamlit as st
import pandas as pd
import osmnx as ox
import networkx as nx
from utils.geo_utils import haversine, filter_stops_within_radius, calculate_midpoint, calculate_zoom_level, interpolate_points
from backend.connect_to_api import ResRobot
from frontend.folium import create_folium_map, add_route_to_map, add_marker_to_map, add_small_marker_to_map, display_map_in_streamlit
from frontend.streamlit_elements import show_departure_timetable

# Initialize ResRobot
resrobot = ResRobot()

# Define city centers (latitude, longitude)
CITY_CENTERS = {
    "Stockholm": (59.3303, 18.0686),
    "Göteborg": (57.7089, 11.9735),
    "Malmö": (55.6096, 13.0007)
}

# Load stops.txt data
@st.cache_data
def load_stops(file_path="data/stops.txt"):
    """Load stop data from a local file."""
    columns = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"]
    return pd.read_csv(file_path, names=columns, header=0)

# Load stops
stops_df = load_stops()
stop_dict = dict(zip(stops_df["stop_name"], stops_df["stop_id"]))

# Streamlit UI
st.title("Public Transport Route Planner")

# Step 1: Select a city
selected_city = st.sidebar.selectbox("Välj stad", list(CITY_CENTERS.keys()))
center_lat, center_lon = CITY_CENTERS[selected_city]

# Step 2: Filter stops within a 150km radius
stops_within_radius = filter_stops_within_radius(stops_df, center_lat, center_lon)

# Create layout
col1, col2, col3 = st.columns([2, 1, 2])

# Step 3: Select Start Point
with col1:
    start_name = st.selectbox("Start Point", [""] + stops_within_radius)
    if start_name:
        st.markdown(f"**Selected Start Point:**<br>{start_name}", unsafe_allow_html=True)

# Arrow symbol
with col2:
    st.markdown("<div style='text-align: center; margin-top: 10px; font-size: 40px;'>→</div>", unsafe_allow_html=True)

# Step 4: Select End Point
with col3:
    end_name = st.selectbox("End Point", [""] + stops_within_radius)
    if end_name:
        st.markdown(f"**Selected End Point:**<br>{end_name}", unsafe_allow_html=True)

# **Handle sidebar dynamically**
st.sidebar.empty()  # Clear sidebar before switching modes

if start_name and not end_name:
    # **Show departure timetable if only start is selected**
    show_departure_timetable(resrobot, stops_df, start_name)

elif start_name and end_name:
    # **Hide departures and show trip details**
    st.sidebar.subheader(f"Trips from {start_name} → {end_name}")

    try:
        start_id = stop_dict[start_name]
        end_id = stop_dict[end_name]

        # Fetch trip details
        trip_details = resrobot.trips(origin_id=start_id, destination_id=end_id)

        if trip_details and "Trip" in trip_details and len(trip_details["Trip"]) > 0:
            for trip in trip_details["Trip"]:
                legs = trip["LegList"]["Leg"]
                if isinstance(legs, dict):  # Handle single-leg trips
                    legs = [legs]

                # Extract trip details
                departure_time = legs[0]["Origin"]["time"]
                arrival_time = legs[-1]["Destination"]["time"]
                route_path = " > ".join([leg["Destination"]["name"].split(" (")[0] for leg in legs])
                transport_number = legs[0]["Product"][0].get("num", "N/A")
                transport_icon = "🚆" if "Tåg" in legs[0]["Product"][0].get("name", "") else "🚍"

                st.sidebar.markdown(f"{transport_icon} {transport_number} → ⏳ {departure_time} - {arrival_time} → {route_path}")

        else:
            st.sidebar.warning("No valid trips found.")

    except KeyError:
        st.sidebar.error("Error: Could not find stop IDs. Please check stop names.")
    except Exception as e:
        st.sidebar.error(f"An error occurred while fetching trip details: {e}")

# **Fetch trip details when both points are selected**
if start_name and end_name:
    st.write(f"**Planning trip:** {start_name} → {end_name}")

    try:
        start_id = stop_dict[start_name]
        end_id = stop_dict[end_name]

        # Fetch trip details
        trip_details = resrobot.trips(origin_id=start_id, destination_id=end_id)

        if trip_details and "Trip" in trip_details and len(trip_details["Trip"]) > 0:
            next_departure = trip_details["Trip"][0]

            # Travel information under "Start Point"
            with col1:
                with st.expander("ℹ️ **Travel Information**", expanded=False):
                    st.subheader("Next Departure Details")
                    st.json(next_departure)

            # Extract coordinates for start & end
            start_stop = stops_df[stops_df["stop_id"] == start_id].iloc[0]
            end_stop = stops_df[stops_df["stop_id"] == end_id].iloc[0]

            # Calculate midpoint & zoom level
            midpoint_lat, midpoint_lon = calculate_midpoint(
                start_stop["stop_lat"], start_stop["stop_lon"],
                end_stop["stop_lat"], end_stop["stop_lon"]
            )
            zoom_level = calculate_zoom_level(
                start_stop["stop_lat"], start_stop["stop_lon"],
                end_stop["stop_lat"], end_stop["stop_lon"]
            )

            # Create Folium map
            m = create_folium_map(midpoint_lat, midpoint_lon, zoom_level)

            # Fetch the road network
            G = ox.graph_from_point((midpoint_lat, midpoint_lon), dist=20000, network_type="drive", simplify=False)

            # Store all route coordinates
            all_route_coords = []

            # Iterate through trip legs
            for leg in next_departure["LegList"]["Leg"]:
                if "Stops" in leg and "Stop" in leg["Stops"]:
                    stops = leg["Stops"]["Stop"]
                    for i in range(len(stops) - 1):
                        current_stop, next_stop = stops[i], stops[i + 1]

                        # Find the nearest nodes in the road network
                        start_node = ox.distance.nearest_nodes(G, current_stop["lon"], current_stop["lat"])
                        end_node = ox.distance.nearest_nodes(G, next_stop["lon"], next_stop["lat"])

                        # Compute shortest path
                        route = nx.shortest_path(G, start_node, end_node, weight="length")

                        # Get route coordinates
                        route_coords = [(G.nodes[node]["y"], G.nodes[node]["x"]) for node in route]

                        # Interpolate points for smooth curves
                        smoothed_route_coords = interpolate_points(route_coords, num_points=100)

                        # Add the smoothed route to the map
                        add_route_to_map(m, smoothed_route_coords)

                        # Store route coordinates
                        all_route_coords.extend(smoothed_route_coords)

            # Add markers and show the map
            add_marker_to_map(m, start_stop["stop_lat"], start_stop["stop_lon"], "Start", "green")
            add_marker_to_map(m, end_stop["stop_lat"], end_stop["stop_lon"], "End", "red")
            with col3:
                with st.expander("🗺️ **Show Map**", expanded=True):
                    display_map_in_streamlit(m)

        else:
            st.error("No departures found for the selected route. Please try again later.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
