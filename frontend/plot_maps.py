<<<<<<< HEAD
import folium
import streamlit as st
from abc import ABC, abstractmethod
import pandas as pd
=======
from abc import ABC, abstractmethod

import folium
import streamlit as st

from backend.trips import TripPlanner

>>>>>>> 94d634fd3100b7974096c49a3ab5e8ab53d068a3

class Maps(ABC):
    """
    Abstract base class for map-related operations.

    Methods:
    --------
    display_map():
        Abstract method to display a map. Must be implemented by subclasses.
    """

    @abstractmethod
    def display_map(self):
        """
        Abstract method to display a map.

        Subclasses must provide an implementation for this method.
        """
        raise NotImplementedError


class TripMap(Maps):
    def __init__(self, trip_data):
        """
        Initialize the TripMap with a DataFrame of trip stops.

        :param trip_data: DataFrame containing "lat", "lon", "name", "time", and optionally "date".
        """
        if not isinstance(trip_data, pd.DataFrame):
            raise ValueError("trip_data must be a pandas DataFrame.")

        required_columns = {"lat", "lon", "name", "time"}
        if not required_columns.issubset(trip_data.columns):
            raise ValueError(f"trip_data must contain columns: {required_columns}")

        self.trip_data = trip_data.drop_duplicates()  # Ensure no duplicate stops

    def _create_map(self):
        """
        Generate a Folium map with markers for each trip stop.
        """
        # Center the map at the first stop
        trip_map = folium.Map(
            location=[self.trip_data["lat"].iloc[0], self.trip_data["lon"].iloc[0]], zoom_start=6
        )

        # Add markers for each stop
        for _, row in self.trip_data.iterrows():
            folium.Marker(
                location=[row["lat"], row["lon"]],
<<<<<<< HEAD
                popup=f"{row['name']}<br>{row['time']}",
                tooltip=row["name"]
            ).add_to(trip_map)

        return trip_map

    def display_map(self):
        """
        Display the map in Streamlit.
        """
        st.markdown("## Resplanens Karta 🗺️")
        st.markdown("Klicka på en station för mer information.")
        trip_map = self._create_map()
        st.components.v1.html(trip_map._repr_html_(), height=500)
=======
                popup=f"{row['name']}<br>{row['time']}<br>{row['date']}",
            ).add_to(geographical_map)

        return geographical_map

    def display_map(self):
        st.markdown("## Karta över stationerna i din resa")
        desc = st.container(border=True)
        desc.markdown(
            "Klicka på varje station för mer information. Detta är en exempelresa mellan Malmö och Umeå"
        )
        m = self._create_map()
        map_html = m._repr_html_()
        styled_html = f"""
        <div style="border: 5px solid #20265A; border-radius: 3px; ">
            {map_html}
        </div>
        """
        st.components.v1.html(styled_html, height=500)
>>>>>>> 94d634fd3100b7974096c49a3ab5e8ab53d068a3
