import re
from datetime import datetime, timedelta

import streamlit as st


def clean_location_name(location):
    """Remove unnecessary suffixes like (Uddevalla kn)."""
    return re.sub(r"\s*\(.*?\)", "", location)


def show_departure_timetable(resrobot, stops_df, start_name, end_name=None):
    """
    Display the departure timetable in the Streamlit sidebar.

    - If only `start_name` is provided: Show `timetable_departure()`.
    - If `end_name` is also provided: **Hide departures** and show full trip details.
    """

    if not start_name:
        return  # Exit if no start station is selected

    # Retrieve stop_id from stops_df
    start_row = stops_df[stops_df["stop_name"] == start_name]
    if start_row.empty:
        st.sidebar.error("Error: Selected start stop not found in dataset.")
        return

    start_id = start_row.iloc[0]["stop_id"]  # Extract start stop_id

    # **CASE 1: Show departures if only the start point is selected**
    if not end_name:
        departures_data = resrobot.timetable_departure(location_id=start_id)
        departures = (
            departures_data.get("Departure", [])
            if isinstance(departures_data, dict)
            else []
        )
        st.sidebar.subheader(
            f"Resor från {start_name}\n{format(datetime.now(), '%H:%M:%S')} - {format(datetime.now() + timedelta(hours=1), '%H:%M:%S')}"  # noqa: E501
        )
        (
            sidecol1,
            sidecol2,
            sidecol3,
        ) = st.sidebar.columns([0.2, 0.29, 0.31], vertical_alignment="top")
        sidecol1.markdown(
            '<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">Linje</div>',
            unsafe_allow_html=True,
        )
        sidecol2.markdown(
            '<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">Avgår om</div>',
            unsafe_allow_html=True,
        )
        sidecol3.markdown("<div style='height: 35px'></div>", unsafe_allow_html=True)
        table_cont = st.sidebar.container(height=520, border=False)
        for dep in departures:
            transport_number = dep.get("ProductAtStop", {}).get(
                "num", dep.get("ProductAtStop", {}).get("name", "N/A")
            )
            departure_time = dep.get("time", "N/A")
            final_destination = clean_location_name(dep.get("direction", "Unknown"))
            stops = dep["Stops"]["Stop"]

            route_detailed = " ➔ ".join(
                [
                    stop["name"].split(" (")[0]
                    + ": "
                    + stop.get("depTime", stop.get("arrTime", "N/A"))
                    for stop in stops
                ]
            )

            t1 = datetime.strptime(departure_time, "%H:%M:%S")
            cur_time = datetime.now()

            if t1 < cur_time:
                wait_time = t1 - cur_time

                hours, minutes = (
                    wait_time.seconds // 3600,
                    wait_time.seconds // 60 % 60,
                )
            else:
                hours, minutes = 0, 0

            if (hours, minutes) == (0, 0) or (hours, minutes) == (23, 59):
                wait = "Nu"
            elif hours == 0:
                wait = f"{minutes}m"
            else:
                wait = f"{hours}h{minutes}m"

            transport_name = dep.get("ProductAtStop", {}).get("name", "N/A")
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
            st.markdown(
                """
            <style>
            .st-emotion-cache-qcpnpn {
            margin-right: 10px;
            </style>
            """,
                unsafe_allow_html=True,
            )
            cont = table_cont.container(border=True)
            tempcol1, tempcol2, tempcol3 = cont.columns(3, vertical_alignment="center")
            tempcol1.markdown(
                f"{transport_icon} {transport_number}", unsafe_allow_html=True
            )
            tempcol2.markdown(
                f'<div style="text-align: right; margin-bottom: 15px; margin-right: 10px">{wait}</div>',
                unsafe_allow_html=True,
            )
            with tempcol3.popover("Info"):
                st.header("Resedetaljer")
                st.write(f"{transport_icon} {transport_number} mot {final_destination}")
                st.markdown(route_detailed)

        return  # Stop execution here if no end stop selected

    # **CASE 2: Both Start & End Stop Selected → Hide departures and show trips**
    st.sidebar.empty()  # **Clear the sidebar** before switching to `trips()`


# another test comment
