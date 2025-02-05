from datetime import datetime

import streamlit as st

from backend.connect_to_api import ResRobot

# **Mapping Transport catCode to Icons**
TRANSPORT_ICONS = {
    "1": "🚆",  # Train
    "2": "🚍",  # Long-distance bus
    "3": "🚆",  # Train
    "4": "🚆",  # Train
    "5": "🚇",  # Subway/Metro
    "6": "🚊",  # Tram
    "7": "🚍",  # Bus
    "unknown": "❓",  # Default for unknown transport types
}


def show_trip_details(
    origin_id, destination_id, date=None, time=None, searchForArrival=0
):
    """Fetch and display trip details from ResRobot's API."""
    resrobot = ResRobot()
    trip_data = resrobot.trips(origin_id, destination_id, date, time, searchForArrival)

    if not trip_data or "Trip" not in trip_data:
        st.warning("🚨 No trips found. Try adjusting the search parameters.")
        return

    # **Initialize session state for trip selection**
    if "selected_trip_index" not in st.session_state:
        st.session_state.selected_trip_index = 0  # Default to Trip[0]

    # Get the current trip based on selection
    selected_trip_index = st.session_state.selected_trip_index
    trips_available = len(trip_data["Trip"])

    # Ensure the index is within range
    if selected_trip_index >= trips_available:
        st.session_state.selected_trip_index = 0  # Reset to first trip
        selected_trip_index = 0

    trip = trip_data["Trip"][selected_trip_index]

    # Extract travel details
    departure_time = trip["LegList"]["Leg"][0]["Origin"]["time"]
    arrival_time = trip["LegList"]["Leg"][-1]["Destination"]["time"]

    # Convert times for calculations
    dep_time_obj = datetime.strptime(departure_time, "%H:%M:%S")
    arr_time_obj = datetime.strptime(arrival_time, "%H:%M:%S")
    travel_duration = arr_time_obj - dep_time_obj

    # Extract transport type using catCode
    leg = trip["LegList"]["Leg"][0]  # First leg of the journey
    transport_type = leg.get("Product", [{}])[0].get("catCode", "unknown")
    transport_number = leg.get("Product", [{}])[0].get("num", "N/A")  # Reintroduced

    # **Determine Transport Icon using catCode**
    transport_icon = TRANSPORT_ICONS.get(str(transport_type), "❓")

    # UI Layout
    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            st.markdown(
                f"### {transport_icon} {transport_number}"
            )  # ✅ Show Transport Number

        with col2:
            st.markdown(f"**Avgång:** {departure_time} ⏩ **Ankomst:** {arrival_time}")
            st.markdown(f"**Tid:** ⏳ {travel_duration}")

        with col3:
            # **Trip Switching Button**
            if trips_available > 1:
                if st.button("➡ Nästa resa"):
                    st.session_state.selected_trip_index = (
                        selected_trip_index + 1
                    ) % trips_available
                    st.rerun()

    st.write("---")  # Divider

    # Show detailed route (all stops)
    st.subheader("Detaljer")
    for leg in trip["LegList"]["Leg"]:
        origin_stop = leg["Origin"]["name"]
        destination_stop = leg["Destination"]["name"]
        dep_time = leg["Origin"]["time"]
        arr_time = leg["Destination"]["time"]
        st.markdown(
            f"**{origin_stop}** ({dep_time}) ➡ **{destination_stop}** ({arr_time})"
        )


# Example Usage (Test within Streamlit)
if __name__ == "__main__":
    st.header("🚌 Trip Details")
    show_trip_details(origin_id=740000001, destination_id=740098001)
