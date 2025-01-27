import streamlit as st

def show_departure_timetable(resrobot, stops_df, start_name, end_name=None):
    """
    Display the departure timetable in the Streamlit sidebar.
    
    - If only `start_name` is provided: Use `timetable_departure()`.
    - If `end_name` is also provided: Use `trips()` to get direct trip details.
    """

    if not start_name:
        return  # Exit if no start station is selected

    # Retrieve stop_id from stops_df
    start_row = stops_df[stops_df["stop_name"] == start_name]
    if start_row.empty:
        st.sidebar.error("Error: Selected start stop not found in dataset.")
        return

    start_id = start_row.iloc[0]["stop_id"]  # Extract start stop_id

    # **CASE 1: Only Start Stop Selected → Use `timetable_departure()`**
    if not end_name:
        departures_data = resrobot.timetable_departure(location_id=start_id)
        if isinstance(departures_data, dict) and "Departure" in departures_data:
            departures = departures_data["Departure"]
        else:
            departures = []

        st.sidebar.subheader(f"Departures from {start_name}")
        for dep in departures:
            transport_number = dep.get("ProductAtStop", {}).get("num", "N/A")
            departure_time = dep.get("time", "N/A")
            final_destination = dep.get("direction", "Unknown")

            transport_icon = "🚆" if "Tåg" in dep.get("ProductAtStop", {}).get("name", "") else "🚍"

            st.sidebar.markdown(f"{transport_icon} **{transport_number}** → ⏳ **{departure_time}** → 📍 **{final_destination}**")

        return  # Stop execution if no end stop selected

    # **CASE 2: Start & End Selected → Use `trips()`**
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
        if isinstance(trips, dict):  # Convert single-trip case to list
            trips = [trips]

        st.sidebar.subheader(f"Trips from {start_name} → {end_name}")

        for trip in trips:
            try:
                # Extract main transport details
                origin = trip["Origin"]
                destination = trip["Destination"]
                transport_name = trip["Product"][0]["name"] if "Product" in trip else "Unknown"
                transport_number = trip["Product"][0]["num"] if "Product" in trip else "N/A"
                departure_time = origin["time"]
                arrival_time = destination["time"]

                # Determine transport type icon
                transport_icon = "🚆" if "Tåg" in transport_name else "🚍"

                # Display result
                st.sidebar.markdown(
                    f"{transport_icon} **{transport_number}** → ⏳ **{departure_time} - {arrival_time}** → 📍 **{destination['name']}**"
                )

            except KeyError:
                continue  # Skip trip if any key is missing

    except Exception as e:
        st.sidebar.error(f"Error fetching trip details: {e}")
