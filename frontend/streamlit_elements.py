import streamlit as st

def show_departure_timetable(resrobot, stops_df, start_name, end_name=None):
    """
    Display the departure timetable in the Streamlit sidebar.
    
    - If only `start_name` is provided: Show all departures from the start station.
    - If `end_name` is also provided: Match departures that align with arrivals at `end_name`.
    """

    if not start_name:
        return  # Exit if no start station is selected

    # Retrieve stop_id from stops_df
    start_row = stops_df[stops_df["stop_name"] == start_name]
    if start_row.empty:
        st.sidebar.error("Error: Selected start stop not found in dataset.")
        return

    start_id = start_row.iloc[0]["stop_id"]  # Extract start stop_id

    # **Fetch Departures from Start Stop**
    departures_data = resrobot.timetable_departure(location_id=start_id)
    departures = departures_data.get("Departure", []) if isinstance(departures_data, dict) else []

    # **If only start point is selected, show all departures**
    if not end_name:
        st.sidebar.subheader(f"Departures from {start_name}")
        for dep in departures:
            transport_name = dep.get("ProductAtStop", {}).get("name", "Unknown")
            transport_number = dep.get("ProductAtStop", {}).get("num", "N/A")
            departure_time = dep.get("time", "N/A")
            final_destination = dep.get("direction", "Unknown")

            transport_icon = "🚆" if "Tåg" in transport_name else "🚍"

            st.sidebar.markdown(f"{transport_icon} **{transport_number}** → ⏳ **{departure_time}** → 📍 **{final_destination}**")

        return  # Stop execution here if no end stop selected

    # **Fetch Arrivals at End Stop**
    end_row = stops_df[stops_df["stop_name"] == end_name]
    if end_row.empty:
        st.sidebar.error("Error: Selected end stop not found in dataset.")
        return

    end_id = end_row.iloc[0]["stop_id"]  # Extract end stop_id
    arrivals_data = resrobot.timetable_arrival(location_id=end_id)
    arrivals = arrivals_data.get("Arrival", []) if isinstance(arrivals_data, dict) else []

    # **Match Arrivals to Departures (FIXED ORDER)**
    matched_trips = []
    
    for arr in arrivals:
        arr_transport = arr.get("ProductAtStop", {}).get("num", "N/A")
        arr_time = arr.get("time", "N/A")
        arr_direction = arr.get("direction", "Unknown")

        # Find the corresponding departure at the start stop
        for dep in departures:
            dep_transport = dep.get("ProductAtStop", {}).get("num", "N/A")
            dep_time = dep.get("time", "N/A")
            dep_final_dest = dep.get("direction", "Unknown")

            # Match if the transport number is the same
            if dep_transport == arr_transport:
                matched_trips.append({
                    "transport": dep_transport,
                    "departure_time": dep_time,  # This should be first now
                    "arrival_time": arr_time,  # This should be second now
                    "destination": dep_final_dest
                })
                break  # Stop searching once a match is found

    # **Display Only Matched Departures**
    st.sidebar.subheader(f"Matched Departures from {start_name} → {end_name}")

    if not matched_trips:
        st.sidebar.warning("No direct matching departures found.")
        return

    for trip in matched_trips:
        transport_icon = "🚆" if "Tåg" in trip["transport"] else "🚍"
        st.sidebar.markdown(
            f"{transport_icon} **{trip['transport']}** → ⏳ **{trip['departure_time']} - {trip['arrival_time']}** → 📍 **{trip['destination']}**"
        )
