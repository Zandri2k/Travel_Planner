from datetime import datetime

import pandas as pd
import streamlit as st

# Import backend classes and functions.
from backend.connect_to_api import ResRobot
from backend.trips import TripPlanner  # Assumes TripPlanner uses ResRobot.trips()

# Import the new search container.
from frontend.search_container import get_full_search_parameters

# Import the timetable display element.
from frontend.streamlit_elements import show_departure_timetable

# Set up the Streamlit page.
st.set_page_config(layout="wide")


# Load stops from your stops.txt file (for autocomplete and mapping stop names to IDs).
@st.cache_data
def load_stops(file_path="data/stops.txt"):
    columns = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"]
    return pd.read_csv(file_path, names=columns, header=0)


stops_df = load_stops()
stop_dict = dict(zip(stops_df["stop_name"], stops_df["stop_id"]))
stops_list = stops_df["stop_name"].tolist()

# Get search parameters from the search container.
search_params = get_full_search_parameters(stops_list)
start_name = search_params.get("start_station", "")
end_name = search_params.get("end_station", "")
date = search_params.get("date", datetime.today().strftime("%Y-%m-%d"))
dep_time = search_params.get("departure_time")  # May be a datetime or None.
arr_time = search_params.get("arrival_time")  # May be a datetime or None.

# Convert active time constraints to strings as expected by the API.
# (If a time constraint is not set, we let the API default be used.)
departure_str = dep_time.strftime("%H:%M") if dep_time is not None else None
arrival_str = arr_time.strftime("%H:%M") if arr_time is not None else None

st.title("Public Transport Route Planner")
st.sidebar.subheader("🛣️ Trip Details")

# If only the start station is selected, show the departures timetable.
if start_name and not end_name:
    st.info("Displaying departures for the selected station.")
    show_departure_timetable(ResRobot(), stops_df, start_name)

# If both start and end stations are selected, attempt to retrieve trip details.
elif start_name and end_name:
    try:
        start_id = stop_dict[start_name]
        end_id = stop_dict[end_name]
    except KeyError:
        st.sidebar.error("🚨 Selected stops are invalid. Please choose valid stops.")
    else:
        # Decide which time constraint to use for the API call.
        # In this example, if both are provided, we assume the user wants:
        #   - Depart after the departure time (if set) and/or
        #   - Arrive before the arrival time (if set)
        #
        # Since the ResRobot API expects a single time and a flag (searchForArrival),
        # we use the following logic:
        #
        # - If only departure time is set: use departure_str and searchForArrival=0.
        # - If only arrival time is set: use arrival_str and searchForArrival=1.
        # - If both are set: you may decide to prioritize one (here, we choose departure).
        # - If neither is set: the API defaults will be used.
        if departure_str and not arrival_str:
            time_val = departure_str
            search_for_arrival = 0
        elif arrival_str and not departure_str:
            time_val = arrival_str
            search_for_arrival = 1
        elif departure_str and arrival_str:
            # If both constraints are provided, you could choose either.
            # Here we decide to prioritize departure time.
            time_val = departure_str
            search_for_arrival = 0
            st.sidebar.info(
                "Both departure and arrival times provided; using departure time for search."
            )
        else:
            # Neither time constraint is provided, so use defaults.
            time_val = datetime.now().strftime("%H:%M")
            search_for_arrival = 0

        # Create a TripPlanner instance and query for trips.
        trip_planner = TripPlanner(start_id, end_id)
        trip_planner.trip_data = trip_planner.resrobot.trips(
            origin_id=start_id,
            destination_id=end_id,
            date=date,
            time=time_val,
            searchForArrival=search_for_arrival,
        )
        trip_planner.extract_route_with_transfers()

        # Display trip details in the sidebar.
        if trip_planner and trip_planner.route_legs:
            for trip in trip_planner.trip_data.get("Trip", []):
                legs = trip["LegList"]["Leg"]
                if isinstance(legs, dict):
                    legs = [legs]
                departure_time_api = legs[0]["Origin"]["time"]
                arrival_time_api = legs[-1]["Destination"]["time"]
                route_path = " > ".join(
                    [leg["Destination"]["name"].split(" (")[0] for leg in legs]
                )
                transport_number = legs[0]["Product"][0].get("num", "N/A")
                transport_icon = (
                    "🚆" if "Tåg" in legs[0]["Product"][0].get("name", "") else "🚌"
                )
                st.sidebar.markdown(
                    f"{transport_icon} {transport_number} → ⏳ {departure_time_api} - {arrival_time_api} → {route_path}"
                )

            # Generate and display the map with the plotted route.
            def generate_and_display_map(tp):
                if not tp:
                    st.warning("❌ No trip data available.")
                    return
                tp.initialize_map()
                for transport_type, stations in tp.route_legs:
                    if transport_type == "4":
                        tp.plot_train_routes(stations)
                    elif transport_type in ["2", "7"]:
                        tp.plot_road_routes(stations)
                    elif transport_type == "3":
                        tp.plot_long_distance_train_routes(stations)
                    elif transport_type == "6":
                        tp.plot_tram_routes(stations)
                    elif transport_type == "5":
                        tp.plot_subway_routes(stations)
                    elif transport_type == "unknown":
                        tp.plot_walking_route(stations[0][1:3], stations[-1][1:3])
                st.components.v1.html(tp.map_route._repr_html_(), height=700)

            generate_and_display_map(trip_planner)
        else:
            st.sidebar.warning("⚠️ No valid trips found.")
else:
    st.info(
        "Please select a start station. To search for trips, also select an end station."
    )
