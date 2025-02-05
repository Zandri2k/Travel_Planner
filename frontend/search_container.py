import calendar
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
# Ratio for the three columns in the station query section.
STATION_QUERY_COLS = [5, 2, 5]
# Number of spacer rows (blank st.write("") calls) under the station query.
STATION_QUERY_SPACER_ROWS = 3
# ------------------ End Adjustable Layout Variables ------------------


def get_full_search_parameters(
    stops_list,
    container_style=CONTAINER_STYLE,
    station_query_cols=STATION_QUERY_COLS,
    station_query_spacer=STATION_QUERY_SPACER_ROWS,
):
    """
    Render a search container that allows selection of:
      - Start and End Stations,
      - Travel Date (restricted to today until the end of the current month),
      - Optionally, a departure time constraint and/or an arrival time constraint.

    For each time constraint, a checkbox determines whether the slider is used.
    If checked, the user picks a time using the slider; if not, the corresponding value is None.

    The slider ranges depend on the selected travel date:
      - If travel_date is today, the available time range is from the current time (rounded
        to the nearest 5 minutes) up to 23:59.
      - Otherwise (for future dates), the range is from 00:00 to 23:59.

    Returns:
      dict: A dictionary with the following keys:
            - "start_station": Selected start station (string).
            - "end_station": Selected end station (string).
            - "date": Selected travel date in "YYYY-MM-DD" format.
            - "departure_time": A datetime object for the departure time constraint, or None.
            - "arrival_time": A datetime object for the arrival time constraint, or None.
    """
    params = {}

    with st.container():
        # Outer container with custom style.
        # st.markdown(f'<div style="{container_style}">', unsafe_allow_html=True)

        # --- Upper Section: Station Query ---
        st.markdown(
            """<span style='
        font-size: 45px;
        font-weight: bold'>Reseplanerare</span>
        """,
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.markdown("Sök resa från en eller mellan två specifika hållplatser.")
            col1, col2, col3 = st.columns(station_query_cols)
            with col1:
                start_station = st.selectbox(
                    "🚏 Från",
                    [""] + stops_list,
                    key="start_station",
                    index=None,
                    placeholder="Stad/Hållplats/Station",
                )
            with col2:
                st.markdown(
                    '<div style="text-align: center; font-size: 40px;">→</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                end_station = st.selectbox(
                    "🚏 Till",
                    [""] + stops_list,
                    key="end_station",
                    index=None,
                    placeholder="Stad/Hållplats/Station",
                )

            # Add spacer rows for vertical space.
            for _ in range(station_query_spacer):
                st.write("")
            params["start_station"] = start_station
            params["end_station"] = end_station

            # --- Lower Section: Date and Time Settings ---
            st.markdown(
                """<span style='
            font-size: 30px;
            font-weight: bold'>Tidsinställningar</span>
            """,
                unsafe_allow_html=True,
            )

            # Date Input: Only allow dates from today until the end of the current month.
            today_date = datetime.today().date()
            current_year = today_date.year
            current_month = today_date.month
            last_day = calendar.monthrange(current_year, current_month)[1]
            last_date_of_month = datetime(current_year, current_month, last_day).date()
            date_col1, date_col2 = st.columns([0.3, 0.7])
            travel_date = date_col1.date_input(
                "Välj resedatum",
                value=today_date,
                min_value=today_date,
                max_value=last_date_of_month,
                key="travel_date",
            )
            params["date"] = travel_date.strftime("%Y-%m-%d")

            # Determine time slider range based on travel_date.
            if travel_date == today_date:
                now = datetime.now()
                # Round current time to the nearest 5 minutes.
                rounded_minute = (now.minute // 5) * 5
                now_rounded = now.replace(
                    minute=rounded_minute, second=0, microsecond=0
                )
                min_time = datetime.combine(travel_date, now_rounded.time())
                default_departure = min_time
            else:
                min_time = datetime.combine(
                    travel_date, datetime.strptime("00:00", "%H:%M").time()
                )
                default_departure = min_time
            max_time = datetime.combine(
                travel_date, datetime.strptime("23:59", "%H:%M").time()
            )
            default_arrival = max_time

            # --- Time Constraint Section ---
            # Two columns: one for departure and one for arrival.
            col_time1, col_time2 = st.columns(2)
            # Departure Time Constraint.
            with col_time1:
                use_departure = st.checkbox("Ange avgångstid", key="use_departure")
                if use_departure:
                    departure_time = st.slider(
                        "Avgångstid",
                        min_value=min_time,
                        max_value=max_time,
                        value=default_departure,
                        step=timedelta(minutes=5),
                        format="HH:mm",
                        key="departure_time",
                    )
                else:
                    departure_time = None

            # Arrival Time Constraint.
            with col_time2:
                use_arrival = st.checkbox("Ange ankomsttid", key="use_arrival")
                if use_arrival:
                    arrival_time = st.slider(
                        "Ankomsttid",
                        min_value=min_time,
                        max_value=max_time,
                        value=default_arrival,
                        step=timedelta(minutes=5),
                        format="HH:mm",
                        key="arrival_time",
                    )
                else:
                    arrival_time = None

            params["departure_time"] = departure_time
            params["arrival_time"] = arrival_time

            # Close the outer container.
            st.markdown("</div>", unsafe_allow_html=True)

    return params


if __name__ == "__main__":
    # For standalone testing only.
    stops_list = ["Stockholm C", "Göteborg C", "Malmö C", "Uppsala C"]
    search_params = get_full_search_parameters(stops_list)
    st.write("Search parameters:", search_params)
