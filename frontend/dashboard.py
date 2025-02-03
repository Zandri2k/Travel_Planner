from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from plot_maps import TripMap

from backend.connect_to_api import ResRobot
from frontend.timetable_sidebar import show_departure_timetable
from utils.constants import StationIds
from utils.geo_utils import filter_stops_within_radius

# Initialize ResRobot
resrobot = ResRobot()

trip_map = TripMap(
    origin_id=StationIds.MALMO.value, destination_id=StationIds.UMEA.value
)

CITY_CENTERS = {
    "Stockholm": (59.3303, 18.0686),
    "Göteborg": (57.7089, 11.9735),
    "Malmö": (55.6096, 13.0007),
}


@st.cache_data
def load_stops(file_path="../data/stops.txt"):
    """Load stop data from a local file."""
    columns = ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"]
    return pd.read_csv(file_path, names=columns, header=0)


@st.dialog("Resedetaljer")
def browse_trip(icon, number, departure_time, arrival_time, path):
    st.write(f"{icon} {number} → ⏳ {departure_time} - {arrival_time} → {path}")


stops_df = load_stops()
stop_dict = dict(zip(stops_df["stop_name"], stops_df["stop_id"]))


img_path = Path(__file__).parent / "images"

test_df = pd.DataFrame(np.random.randn(10, 2), columns=(["Linje", "Avgår om (min)"]))


def main():
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

    selected_city = st.sidebar.selectbox("Välj stad", list(CITY_CENTERS.keys()))
    center_lat, center_lon = CITY_CENTERS[selected_city]

    stops_within_radius = filter_stops_within_radius(stops_df, center_lat, center_lon)

    st.markdown(
        """<span style='
        color: #20265A;
        font-size: 70px;
        font-weight: bold'>Resekollen</span>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("# Reseplanerare")
    desc = st.container(border=True)
    desc.markdown(
        "Här visas stopp och andra detaljer för en resa mellan två valda resmål"
    )
    col1, col2, col3 = st.columns([0.45, 0.1, 0.45])
    start_name = col1.selectbox(
        "Från",
        [""] + stops_within_radius,
        index=None,
        placeholder="Stad/Hållplats/Station",
    )
    col2.markdown(
        "<div style='text-align: center; margin-top: 10px; font-size: 40px;'>→</div>",
        unsafe_allow_html=True,
    )
    end_name = col3.selectbox(
        "Till",
        [""] + stops_within_radius,
        index=None,
        placeholder="Stad/Hållplats/Station",
    )

    if start_name and not end_name:
        # **Show departure timetable if only start is selected**
        show_departure_timetable(resrobot, stops_df, start_name)
    elif start_name and end_name:
        # **Hide departures and show trip details**
        st.sidebar.subheader(f"Resor från {start_name} → {end_name}")

        try:
            start_id = stop_dict[start_name]
            end_id = stop_dict[end_name]

            # Fetch trip details
            trip_details = resrobot.trips(origin_id=start_id, destination_id=end_id)

            if (
                trip_details
                and "Trip" in trip_details
                and len(trip_details["Trip"]) > 0
            ):
                sidecol1, sidecol2, sidecol3, sidecol4 = st.sidebar.columns(
                    4, vertical_alignment="top"
                )
                sidecol1.markdown("Linje")
                sidecol2.markdown("Avgår om")
                sidecol3.markdown("Restid")
                sidecol4.markdown(
                    "<div style='height: 35px'></div>", unsafe_allow_html=True
                )
                cur_time = datetime.now()
                for trip in trip_details["Trip"]:
                    legs = trip["LegList"]["Leg"]
                    if isinstance(legs, dict):  # Handle single-leg trips
                        legs = [legs]

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

                    route_path = " > ".join(
                        [leg["Destination"]["name"].split(" (")[0] for leg in legs]
                    )
                    transport_number = legs[0]["Product"][0].get("num", "N/A")
                    transport_icon = (
                        "🚆" if "Tåg" in legs[0]["Product"][0].get("name", "") else "🚍"
                    )
                    cont = st.sidebar.container(border=True)
                    tempcol1, tempcol2, tempcol3, tempcol4 = cont.columns(
                        4, vertical_alignment="center"
                    )
                    tempcol1.markdown(
                        f"{transport_icon} {transport_number}", unsafe_allow_html=True
                    )
                    tempcol2.markdown(
                        f'<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">{wait}</div>',
                        unsafe_allow_html=True,
                    )
                    tempcol3.markdown(f"⏳ {hours}h{minutes}m", unsafe_allow_html=True)
                    with tempcol4.popover("Info", use_container_width=True):
                        st.write(
                            f"{transport_icon} {transport_number} → ⏳ {departure_time} - {arrival_time} → {route_path}"
                        )

            else:
                st.sidebar.warning("No valid trips found.")

        except KeyError:
            st.sidebar.error("Error: Could not find stop IDs. Please check stop names.")
        except Exception as e:
            st.sidebar.error(f"An error occurred while fetching trip details: {e}")


if __name__ == "__main__":
    main()

# Test comment
