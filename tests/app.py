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

# Streamlit UI
st.title("Public Transport Route Planner")

# Step 1: Let the user select a city (small selectbox in the corner)
selected_city = st.sidebar.selectbox("Välj stad", list(CITY_CENTERS.keys()))

# Get the city center coordinates
center_lat, center_lon = CITY_CENTERS[selected_city]

# Step 2: Filter stops within a 150km radius of the selected city
stops_within_radius = filter_stops_within_radius(stops_df, center_lat, center_lon)



# Create a layout with three columns: Start Point, Arrow, End Point
col1, col2, col3 = st.columns([2, 1, 2])

# Step 3: Selectbox for start and end points (empty by default)
with col1:
    start_name = st.selectbox("Start Point", [""] + stops_within_radius)
    if start_name:
        st.markdown(f"**Selected Start Point:**<br>{start_name}", unsafe_allow_html=True)
        
# Show the timetable only if a start station is selected
if start_name:
    show_departure_timetable(resrobot, stops_df, start_name)


with col2:
    # Lower the arrow slightly using CSS
    st.markdown(
        "<div style='text-align: center; margin-top: 10px; font-size: 40px;'>→</div>",
        unsafe_allow_html=True
    )

with col3:
    end_name = st.selectbox("End Point", [""] + stops_within_radius)
    if end_name:
        st.markdown(f"**Selected End Point:**<br>{end_name}", unsafe_allow_html=True)

# Fetch trip details when both points are selected
if start_name and end_name:
    st.write(f"**Planning trip:** {start_name} → {end_name}")

    # Get stop IDs (remove the city part from the formatted name)
    start_id = stop_dict[start_name.split(", ")[0]]
    end_id = stop_dict[end_name.split(", ")[0]]

    # Fetch the next departure using the ResRobot API
    try:
        trip_details = resrobot.trips(origin_id=start_id, destination_id=end_id)

        if trip_details and "Trip" in trip_details and len(trip_details["Trip"]) > 0:
            next_departure = trip_details["Trip"][0]  # Take the first trip (next departure)

            # Travel information under "Start Point"
            with col1:
                with st.expander("ℹ️ **Travel Information**", expanded=False):
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
            m = create_folium_map(midpoint_lat, midpoint_lon, zoom_level)

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
                        add_route_to_map(m, smoothed_route_coords)

                        # Add the coordinates to the list of all route coordinates
                        all_route_coords.extend(smoothed_route_coords)

            # Add markers for the start and end points
            add_marker_to_map(m, start_stop["stop_lat"], start_stop["stop_lon"], f"Start: {start_name}", "green")
            add_marker_to_map(m, end_stop["stop_lat"], end_stop["stop_lon"], f"End: {end_name}", "red")

            # Add smaller markers for each stop along the route
            for leg in next_departure["LegList"]["Leg"]:
                if "Stops" in leg and "Stop" in leg["Stops"]:
                    for stop in leg["Stops"]["Stop"]:
                        add_small_marker_to_map(m, stop["lat"], stop["lon"], f"{stop['name']}<br>{stop.get('arrTime', stop.get('depTime', 'N/A'))}")

            # Map under "End Point"
            with col3:
                with st.expander("🗺️ **Show Map**", expanded=True):
                    display_map_in_streamlit(m)

        else:
            st.error("No departures found for the selected route. Please try again later.")

    except Exception as e:
        st.error(f"An error occurred while fetching trip details: {e}")

elif start_name or end_name:
    st.info("Please select both start and end points.")
