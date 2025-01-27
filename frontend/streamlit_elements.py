import streamlit as st
import requests

def show_departure_timetable(resrobot, stops_df, start_name):
    """
    Display the departure timetable in the Streamlit sidebar.
    
    - Fetches departures for the selected start station.
    - Displays options in a dropdown.
    - Shows details for the selected departure.
    """

    if not start_name:
        return  # Exit if no start station is selected

    # Retrieve the stop_id from stops_df based on start_name
    stop_row = stops_df[stops_df["stop_name"] == start_name]
    if stop_row.empty:
        st.sidebar.error("Error: Selected stop not found in dataset.")
        return

    stop_id = stop_row.iloc[0]["stop_id"]  # Get the corresponding stop_id

    # Sidebar header
    st.sidebar.subheader(f"Departures from {start_name}")

    try:
        departures_data = resrobot.timetable_departure(location_id=stop_id)

        if departures_data and "Departure" in departures_data:
            departures = departures_data["Departure"]

            # Format departure options
            departure_options = [
                f"{dep['time']} → {dep['direction']}" for dep in departures
            ]

            # User selects a departure (optional)
            selected_departure = st.sidebar.selectbox("Select a Departure", [""] + departure_options)

            # Show details if a departure is selected
            if selected_departure:
                selected_dep_index = departure_options.index(selected_departure) - 1
                selected_dep_data = departures[selected_dep_index]

                with st.sidebar.expander("📌 Departure Details", expanded=True):
                    st.write(f"**Time:** {selected_dep_data['time']}")
                    st.write(f"**Destination:** {selected_dep_data['direction']}")
                    st.write(f"**Track:** {selected_dep_data.get('track', 'N/A')}")
                    st.write(f"**Operator:** {selected_dep_data.get('Product', {}).get('operator', 'Unknown')}")

        else:
            st.sidebar.warning("No departures available for this stop.")

    except Exception as e:
        st.sidebar.error(f"Error fetching timetable: {e}")
