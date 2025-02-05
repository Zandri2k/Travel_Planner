from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from backend.connect_to_api import ResRobot
from backend.trips import TripPlanner  # Assumes TripPlanner uses ResRobot.trips()

# Import the new search container.
from frontend.search_container import get_full_search_parameters
from frontend.timetable_sidebar import show_departure_timetable

# Initialize ResRobot
resrobot = ResRobot()

IMAGE_PATH = "../frontend/images"
light_logo = f"{IMAGE_PATH}/Resekollen_logo_700.png"
dark_logo = f"{IMAGE_PATH}/Resekollen_logo_700_dark.png"


@st.cache_data
def load_stops(file_path="../data/stops.txt"):
    """Load stop data from a local file."""
    columns = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"]
    return pd.read_csv(file_path, names=columns, header=0)


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


def generate_and_display_map(tp):
    if not tp:
        st.warning("❌ No trip data available.")
        return
    tp.initialize_map()
    for i, (transport_type, stations) in enumerate(tp.route_legs):
        if transport_type in [
            "1",
            "3",
            "4",
        ]:  # Fix: Check string, not list in # in ["1", "3", "4"]
            tp.plot_train_routes(tp.map_route, stations)
        elif transport_type in ["2", "7"]:  # Includes both long-distance bus and metro
            tp.plot_road_routes(tp.map_route, stations)
        elif transport_type == "6":
            tp.plot_tram_routes(tp.map_route, stations)
        elif transport_type == "5":
            tp.plot_subway_routes(tp.map_route, stations)  # ✅ Subway plotting function
        elif transport_type == "unknown" and i > 0:
            # 🚨 FIX: Correctly use the last station from the previous leg as the start
            start = tp.route_legs[i - 1][1][-1][1:3]  # Last stop of previous leg
            end = stations[-1][1:3]  # Last stop of current leg
            print(f"🚶 Walking route correctly assigned: Start {start} → End {end}")
            tp.plot_walking_route(tp.map_route, start, end)
    map_html = tp.map_route._repr_html_()
    styled_html = f"""
    <div style="border: 5px solid #20265A; border-radius: 3px; ">
        {map_html}
    </div>
    """
    st.components.v1.html(styled_html, height=700)


stops_df = load_stops()
stop_dict = dict(zip(stops_df["stop_name"], stops_df["stop_id"]))
stops_list = stops_df["stop_name"].to_list()


img_path = Path(__file__).parent / "images"


def main():

    st.html(
        """
    <style>
        [alt=Logo] {
        height: 175px;
        }
    </style>
    """
    )

    st.logo(
        light_logo,
        size="large",
        icon_image=dark_logo,
    )

    st.markdown(
        """
    <style>
    .st-emotion-cache-yw8pof {
    max-width: 75rem;
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <style>
        section[data-testid="stSidebar"] {
            width: 455px !important; # Set the width to your desired value
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Tidstabell")

    st.markdown(
        """<span style='
        color: #20265A;
        font-size: 70px;
        font-weight: bold'>Resekollen</span>
        """,
        unsafe_allow_html=True,
    )

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

    if start_name and not end_name:
        # **Show departure timetable if only start is selected**
        show_departure_timetable(resrobot, stops_df, start_name)
    elif start_name and end_name:
        # **Hide departures and show trip details**
        st.sidebar.subheader(f"Resor från {start_name} → {end_name}")

        try:
            start_id = stop_dict[start_name]
            end_id = stop_dict[end_name]

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

            if trip_planner and trip_planner.route_legs:
                sidecol1, sidecol2, sidecol3, sidecol4 = st.sidebar.columns(
                    4, vertical_alignment="top"
                )
                sidecol1.markdown(
                    '<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">Linje</div>',
                    unsafe_allow_html=True,
                )
                sidecol2.markdown(
                    '<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">Avgår om</div>',
                    unsafe_allow_html=True,
                )
                sidecol3.markdown(
                    '<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">Restid</div>',
                    unsafe_allow_html=True,
                )
                sidecol4.markdown(
                    "<div style='height: 35px'></div>", unsafe_allow_html=True
                )
                cur_time = datetime.now()
                button_key = 0
                for trip in trip_planner.trip_data.get("Trip", []):
                    legs = trip["LegList"]["Leg"]
                    changes = len(legs) - 1
                    print(changes)
                    if isinstance(legs, dict):  # Handle single-leg trips
                        legs = [legs]
                    stops = []
                    for leg in legs:
                        if "Stops" in leg:
                            stops += leg["Stops"]["Stop"]

                    route_detailed = " ➔ ".join(
                        [
                            stop["name"].split(" (")[0]
                            + ": "
                            + stop.get("depTime", stop.get("arrTime", "N/A"))
                            for stop in stops
                        ]
                    )

                    # Extract trip details
                    departure_time = legs[0]["Origin"]["time"]
                    arrival_time = legs[-1]["Destination"]["time"]
                    t1 = datetime.strptime(departure_time, "%H:%M:%S")
                    t2 = datetime.strptime(arrival_time, "%H:%M:%S")

                    travel_time = t2 - t1

                    if t1 < cur_time:
                        wait_time = t1 - cur_time

                        hours, minutes = (
                            wait_time.seconds // 3600,
                            wait_time.seconds // 60 % 60,
                        )
                    else:
                        hours, minutes = 0, 0

                    if (hours, minutes) == (0, 0):
                        wait = "Nu"
                    elif hours == 0:
                        wait = f"{minutes}m"
                    else:
                        wait = f"{hours}h{minutes}m"

                    hours, minutes = (
                        travel_time.seconds // 3600,
                        travel_time.seconds // 60 % 60,
                    )
                    transport_name = legs[0]["Product"][0].get("name", "")
                    transport_number = legs[0]["Product"][0].get(
                        "num", legs[0]["Product"][0].get("name", "N/A")
                    )
                    transport_icon = "N/A"
                    icons = ["🚆", "🚍", "🚊", "🚇", "🚶", "🚄", "🚄"]
                    transport_types = [
                        "Tåg",
                        "Buss",
                        "Spårväg",
                        "Tunnelbana",
                        "Promenad",
                        "Snabbtåg",
                        "Express",
                    ]
                    for i, t in zip(icons, transport_types):
                        if t in transport_name:
                            transport_icon = i

                    cont = st.sidebar.container(border=True)
                    tempcol1, tempcol2, tempcol3, tempcol4 = cont.columns(
                        [0.3, 0.2, 0.25, 0.25], vertical_alignment="center"
                    )
                    tempcol1.markdown(
                        f'<div style="margin-bottom: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; ">{transport_icon} {transport_number}</div>',  # noqa: E501
                        unsafe_allow_html=True,
                    )
                    tempcol2.markdown(
                        f'<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">{wait}</div>',
                        unsafe_allow_html=True,
                    )
                    tempcol3.markdown(f"⏳ {hours}h{minutes}m", unsafe_allow_html=True)
                    with tempcol4.popover("Info", use_container_width=True):
                        st.header("Resedetaljer")
                        st.write(f"{transport_icon} {transport_name} mot {end_name}")
                        st.markdown(route_detailed)
                        if st.button("Välj resa", key=f"select_trip_{button_key}"):
                            st.session_state.selected_trip = {
                                "transport_icon": transport_icon,
                                "transport_number": transport_number,
                                "departure_time": departure_time,
                                "arrival_time": arrival_time,
                                "route": route_detailed,
                                "stops": stops,
                                "changes": changes,
                            }

                            st.rerun()  # Refresh
                        button_key += 1

                generate_and_display_map(trip_planner)
            else:
                st.sidebar.warning("No valid trips found.")

        except KeyError:
            st.sidebar.error("Error: Could not find stop IDs. Please check stop names.")
        except Exception as e:
            st.sidebar.error(f"An error occurred while fetching trip details: {e}")

        # Details of the chosen trip
    if "selected_trip" in st.session_state and st.session_state.selected_trip:
        selected = st.session_state.selected_trip

        with st.container(border=True):
            st.subheader(f"📌Tåg mot {end_name}")

            st.divider()  # Adds separation
            st.write(f"**{selected['transport_icon']} {selected['transport_number']}**")
            st.write(
                f"⏳ Avgång: {selected['departure_time']} | 🏁 Ankomst: {selected['arrival_time']}"
            )

            st.write(f"Antal stop:{len(selected['stops']) -1}")
            st.write(f"Antal byten:{selected['changes']}")

            route_detailed = [stop["name"].split(" (")[0] for stop in stops]
            list_of_stops = st.selectbox("Visa alla stop", route_detailed)
            st.write(f"Valt stop: {list_of_stops}")

        # Reset button to clear the selection
        if st.button("❌ Avbryt vald resa"):
            st.session_state.start_name = ""
            st.session_state.end_name = ""
            st.session_state.selected_trip = None
            st.rerun()


if __name__ == "__main__":
    main()

# Test comment
