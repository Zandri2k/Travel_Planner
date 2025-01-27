import streamlit as st

def show_departure_timetable(resrobot, stops_df, start_name):
    """
    Display the departure timetable in the Streamlit sidebar.
    
    - Fetches departures for the selected start station.
    - Lists departures with transport name, departure time, arrival time, and destination.
    """

    if not start_name:
        return  # Exit if no start station is selected

    # Retrieve the stop_id from stops_df based on start_name
    stop_row = stops_df[stops_df["stop_name"] == start_name]

    if stop_row.empty:
        st.sidebar.error("Error: Selected stop not found in dataset.")
        return

    stop_id = stop_row.iloc[0]["stop_id"]  # Extract a single stop_id value

    # Sidebar header
    st.sidebar.subheader(f"Departures from {start_name}")

    try:
        # Fetch departures using stop_id
        departures_data = resrobot.timetable_departure(location_id=stop_id)
        if isinstance(departures_data, dict) and "Departure" in departures_data:  
            departures = departures_data["Departure"]  # Extract departures if dict
        else:
            st.sidebar.warning("No departures available.")
            return

        # Display each departure in a simple, clear format
        for dep in departures:
            transport_info = dep.get("ProductAtStop", {})
            transport_name = transport_info.get("name", "Unknown")
            transport_number = transport_info.get("displayNumber", "N/A")
            operator = transport_info.get("operator", "Unknown")
            departure_time = dep.get("time", "N/A")
            final_destination = dep.get("direction", "Unknown")

            # Determine transport type (Bus or Train)
            transport_icon = "🚆" if "Tåg" in transport_name else "🚍"

            # Format output in sidebar
            st.sidebar.markdown(
                f"{transport_icon} **{transport_name} ({transport_number})** "
                f"→ ⏳ **{departure_time} - ❓** "
                f"→ 📍 **{final_destination}**"
            )

    except Exception as e:
        st.sidebar.error(f"Error fetching timetable: {e}")
