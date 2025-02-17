import re

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

        st.sidebar.subheader(f"Departures from {start_name}")

        for dep in departures:
            transport_number = dep.get("ProductAtStop", {}).get("num", "N/A")
            departure_time = dep.get("time", "N/A")
            final_destination = clean_location_name(dep.get("direction", "Unknown"))

            transport_icon = (
                "🚆" if "Tåg" in dep.get("ProductAtStop", {}).get("name", "") else "🚍"
            )

            st.sidebar.markdown(
                f"{transport_icon} {transport_number} → ⏳ {departure_time} → 📍 {final_destination}"
            )

        return  # Stop execution here if no end stop selected

    # **CASE 2: Both Start & End Stop Selected → Hide departures and show trips**
    st.sidebar.empty()  # **Clear the sidebar** before switching to `trips()`

    end_row = stops_df[stops_df["stop_name"] == end_name]
    if end_row.empty:
        st.sidebar.error("Error: Selected end stop not found in dataset.")
        return

    end_id = end_row.iloc[0]["stop_id"]  # Extract end stop_id

    try:
        trips_data = resrobot.trips(origin_id=start_id, destination_id=end_id)
        if not isinstance(trips_data, dict) or "Trip" not in trips_data:
            st.sidebar.warning("No valid trips found.")
            return

        trips = trips_data["Trip"]
        if isinstance(trips, dict):  # Handle single-trip case
            trips = [trips]

        st.sidebar.subheader(f"Trips from {start_name} → {end_name}")

        for trip in trips:
            try:
                # Build the A > B > C route format without suffixes
                route_path = [clean_location_name(trip["Origin"]["name"])]
                for leg in trip["LegList"]["Leg"]:
                    route_path.append(clean_location_name(leg["Destination"]["name"]))
                route_string = " > ".join(route_path)

                # Extract transport details from the first leg
                first_leg = trip["LegList"]["Leg"][0]
                transport_info = first_leg.get("Product", [{}])[
                    0
                ]  # First transport entry
                transport_number = transport_info.get("num", "N/A")

                # Extract departure and arrival details
                departure_time = first_leg["Origin"]["time"]
                arrival_time = first_leg["Destination"]["time"]

                # Determine transport type icon
                transport_icon = (
                    "🚆" if "Tåg" in transport_info.get("name", "") else "🚍"
                )

                # Display in sidebar
                st.sidebar.markdown(
                    f"{transport_icon} {transport_number} → ⏳ {departure_time} - {arrival_time} → {route_string}"
                )

            except KeyError:
                st.sidebar.warning("Some trip details are missing.")

    except Exception as e:
        st.sidebar.error(f"Error fetching trip details: {e}")
