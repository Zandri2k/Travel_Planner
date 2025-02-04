from datetime import datetime, timedelta

import streamlit as st

# ------------------ Adjustable Layout Variables ------------------
CONTAINER_STYLE = (
    "border: 1px solid rgba(0,0,0,0.2); "  # Faded outline
    "border-radius: 8px; "
    "padding: 20px; "
    "background-color: #f9f9f9; "
    "margin: 10px 0px;"
)
# Adjust the ratio for the three columns in the station query section.
STATION_QUERY_COLS = [5, 2, 5]
# Number of spacer rows (blank st.write("") calls) under station query.
STATION_QUERY_SPACER_ROWS = 5
# ------------------ End Adjustable Variables ------------------


def get_full_search_parameters(
    stops_list,
    container_style=CONTAINER_STYLE,
    station_query_cols=STATION_QUERY_COLS,
    station_query_spacer=STATION_QUERY_SPACER_ROWS,
):
    """
    Render a search container with station and time settings wrapped in a styled box.

    Parameters:
      stops_list (list): List of stops for the selectboxes.
      container_style (str): CSS style for the outer container.
      station_query_cols (list): List defining the relative widths of the three columns.
      station_query_spacer (int): Number of blank lines to add under the station query.

    Returns:
      dict: Dictionary with:
            - "start_station": Selected start station.
            - "end_station": Selected end station.
            - "date": Selected travel date (YYYY-MM-DD).
            - "time_option": One of "Nu", "Avgångstid", "Ankomstid".
            - "selected_time": The chosen time (datetime object) if applicable.
    """
    params = {}

    with st.container():
        # Outer styled container with faded outline.
        st.markdown(f"<div style='{container_style}'>", unsafe_allow_html=True)

        # --- Upper Section (approx. 8 rows): Station Query ---
        st.markdown("## Station Query")
        col1, col2, col3 = st.columns(station_query_cols)
        with col1:
            start_station = st.selectbox(
                "🚏 Start Point", [""] + stops_list, key="start_station"
            )
        with col2:
            st.markdown(
                "<div style='text-align: center; font-size: 40px;'>→</div>",
                unsafe_allow_html=True,
            )
        with col3:
            end_station = st.selectbox(
                "🚏 End Point", [""] + stops_list, key="end_station"
            )
        # Add blank spacer rows for extra vertical space.
        for _ in range(station_query_spacer):
            st.write("")
        params["start_station"] = start_station
        params["end_station"] = end_station

        # --- Lower Section (approx. 4 rows): Date and Time Settings ---
        st.markdown("## Tidinställningar")

        # Row 1: Date selector (for the timetable schedule).
        travel_date = st.date_input(
            "Välj resedatum", value=datetime.today(), key="travel_date"
        )
        params["date"] = travel_date.strftime("%Y-%m-%d")

        # Row 2: Horizontal radio for time mode.
        time_option = st.radio(
            "",
            options=["Nu", "Avgångstid", "Ankomstid"],
            index=0,
            horizontal=True,
            key="time_option",
        )
        params["time_option"] = time_option

        # Rows 3-4: Conditional expander with a time slider.
        selected_time = None
        if time_option in ("Avgångstid", "Ankomstid"):
            expander_label = (
                "Välj avgångstid" if time_option == "Avgångstid" else "Välj ankomsttid"
            )
            with st.expander(expander_label, expanded=False):
                now = datetime.now()
                min_time = now - timedelta(hours=6)
                max_time = now + timedelta(hours=6)
                selected_time = st.slider(
                    "Välj tid",
                    min_value=min_time,
                    max_value=max_time,
                    value=now,
                    step=timedelta(minutes=5),
                    format="HH:mm",
                    key="selected_time",
                )
        params["selected_time"] = selected_time

        # Close the outer container.
        st.markdown("</div>", unsafe_allow_html=True)

    return params


# --- Example usage for testing in isolation ---
if __name__ == "__main__":
    # Example stops list; in your actual app, load this from your stops.txt file.
    stops_list = ["Stockholm C", "Göteborg C", "Malmö C", "Uppsala C"]
    search_params = get_full_search_parameters(stops_list)
    st.write("Search parameters:", search_params)
