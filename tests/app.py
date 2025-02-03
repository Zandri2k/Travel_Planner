import pandas as pd
import streamlit as st

from backend.connect_to_api import ResRobot
from backend.trips import TripPlanner  # ✅ Import your TripPlanner class
from frontend.streamlit_elements import show_departure_timetable
from utils.geo_utils import filter_stops_within_radius

resrobot = ResRobot()
# 🎯 Define City Centers
CITY_CENTERS = {
    "Stockholm": (59.3303, 18.0686),
    "Göteborg": (57.7089, 11.9735),
    "Malmö": (55.6096, 13.0007),
}


# ✅ Load Stops Data (Cached for Performance)
@st.cache_data
def load_stops(file_path="data/stops.txt"):
    columns = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"]
    return pd.read_csv(file_path, names=columns, header=0)


stops_df = load_stops()
stop_dict = dict(zip(stops_df["stop_name"], stops_df["stop_id"]))


# ✅ Hook 1: Fetch Trip Data and Create a `TripPlanner` Instance
def get_trip_planner(start_name, end_name):
    """Fetches trip details and returns a TripPlanner instance."""
    if not start_name or not end_name:
        return None

    try:
        start_id = stop_dict[start_name]
        end_id = stop_dict[end_name]
        trip_planner = TripPlanner(start_id, end_id)
        trip_planner.extract_route_with_transfers()
        return trip_planner
    except KeyError:
        st.sidebar.error("🚨 Stop IDs not found. Please select valid stops.")
        return None


# ✅ Hook 2: Generate and Display Map
def generate_and_display_map(trip_planner):
    """Generates the map using TripPlanner and displays it in Streamlit."""
    if not trip_planner:
        st.warning("❌ No trip data available.")
        return

    trip_planner.initialize_map()

    for transport_type, stations in trip_planner.route_legs:
        print(f"📌 Processing leg: Type = {transport_type}")

        if transport_type == "4":
            trip_planner.plot_train_routes(stations)
        elif transport_type in ["2", "7"]:  # Buses
            trip_planner.plot_road_routes(stations)
        elif transport_type == "3":
            trip_planner.plot_long_distance_train_routes(stations)
        elif transport_type == "6":
            trip_planner.plot_tram_routes(stations)
        elif transport_type == "5":
            trip_planner.plot_subway_routes(stations)
        elif transport_type == "unknown":
            trip_planner.plot_walking_route(stations[0][1:3], stations[-1][1:3])

    st.components.v1.html(trip_planner.map_route._repr_html_(), height=700)


# 🎯 **Streamlit UI**
st.title("Public Transport Route Planner")

# ✅ Sidebar: Select a City
selected_city = st.sidebar.selectbox("🏙️ Select City", list(CITY_CENTERS.keys()))
center_lat, center_lon = CITY_CENTERS[selected_city]

# ✅ Filter stops based on the selected city
stops_within_radius = filter_stops_within_radius(stops_df, center_lat, center_lon)

# 🏙️ Select Start & End Points
col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    start_name = st.selectbox("🚏 Start Point", [""] + stops_within_radius)
with col2:
    st.markdown(
        "<div style='text-align: center; font-size: 40px;'>→</div>",
        unsafe_allow_html=True,
    )
with col3:
    end_name = st.selectbox("🚏 End Point", [""] + stops_within_radius)

# **Sidebar: Trip Information**
st.sidebar.subheader("🛣️ Trip Details")

if start_name and not end_name:
    # **Show departure timetable if only start is selected**
    show_departure_timetable(resrobot, stops_df, start_name)

elif start_name and end_name:
    # **Fetch trip details**
    trip_planner = get_trip_planner(start_name, end_name)

    if trip_planner and trip_planner.route_legs:
        for trip in trip_planner.trip_data.get("Trip", []):
            legs = trip["LegList"]["Leg"]
            if isinstance(legs, dict):  # Handle single-leg trips
                legs = [legs]

            # Extract trip details
            departure_time = legs[0]["Origin"]["time"]
            arrival_time = legs[-1]["Destination"]["time"]
            route_path = " > ".join(
                [leg["Destination"]["name"].split(" (")[0] for leg in legs]
            )
            transport_number = legs[0]["Product"][0].get("num", "N/A")
            transport_icon = (
                "🚆" if "Tåg" in legs[0]["Product"][0].get("name", "") else "🚌"
            )

            st.sidebar.markdown(
                f"{transport_icon} {transport_number} → ⏳ {departure_time} - {arrival_time} → {route_path}"
            )

        generate_and_display_map(trip_planner)

    else:
        st.sidebar.warning("⚠️ No valid trips found.")
