from datetime import datetime

import pandas as pd
import streamlit as st

from backend.connect_to_api import ResRobot
from backend.trips import TripPlanner  # Your existing TripPlanner remains unchanged
from frontend.search_container import (  # The combined search container
    get_full_search_parameters,
)
from frontend.streamlit_elements import show_departure_timetable

st.set_page_config(layout="wide")


# Load full stops list (no regional filtering)
@st.cache_data
def load_stops(file_path="data/stops.txt"):
    columns = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"]
    return pd.read_csv(file_path, names=columns, header=0)


stops_df = load_stops()
stop_dict = dict(zip(stops_df["stop_name"], stops_df["stop_id"]))
stops_list = stops_df["stop_name"].tolist()

# Use the new search container to capture all parameters.
search_params = get_full_search_parameters(stops_list)
start_name = search_params["start_station"]
end_name = search_params["end_station"]
date = search_params["date"]
# If a timed option was selected ("Avgångstid" or "Ankomstid"), use the slider value; otherwise, fallback
time_val = (
    search_params["selected_time"].strftime("%H:%M")
    if search_params["time_option"] in ("Avgångstid", "Ankomstid")
    else datetime.now().strftime("%H:%M")
)
search_for_arrival = 1 if search_params["time_option"] == "Ankomstid" else 0

st.title("Public Transport Route Planner")
st.sidebar.subheader("🛣️ Trip Details")

# If only start station is selected, show departures.
if start_name and not end_name:
    show_departure_timetable(ResRobot(), stops_df, start_name)

# If both stations are selected, fetch and display trip details.
elif start_name and end_name:

    def get_trip_planner(start_name, end_name, date, time_val, search_for_arrival):
        if not start_name or not end_name:
            return None
        try:
            start_id = stop_dict[start_name]
            end_id = stop_dict[end_name]
            # Create TripPlanner and override trip_data with a query that includes time parameters.
            trip_planner = TripPlanner(start_id, end_id)
            trip_planner.trip_data = trip_planner.resrobot.trips(
                origin_id=start_id,
                destination_id=end_id,
                date=date,
                time=time_val,
                searchForArrival=search_for_arrival,
            )
            trip_planner.extract_route_with_transfers()
            return trip_planner
        except KeyError:
            st.sidebar.error("🚨 Stop IDs not found. Please select valid stops.")
            return None

    trip_planner = get_trip_planner(
        start_name, end_name, date, time_val, search_for_arrival
    )

    if trip_planner and trip_planner.route_legs:
        # Display trip details in the sidebar.
        for trip in trip_planner.trip_data.get("Trip", []):
            legs = trip["LegList"]["Leg"]
            if isinstance(legs, dict):
                legs = [legs]
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

        # Generate and display the map.
        def generate_and_display_map(trip_planner):
            if not trip_planner:
                st.warning("❌ No trip data available.")
                return
            trip_planner.initialize_map()
            for transport_type, stations in trip_planner.route_legs:
                if transport_type == "4":
                    trip_planner.plot_train_routes(stations)
                elif transport_type in ["2", "7"]:
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

        generate_and_display_map(trip_planner)
    else:
        st.sidebar.warning("⚠️ No valid trips found.")
