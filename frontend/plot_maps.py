import folium
from backend.trips import TripPlanner
import streamlit as st
from abc import ABC, abstractmethod


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
    def __init__(self, origin_id, destination_id):
        trip_planner = TripPlanner(origin_id, destination_id)
        self.next_trip = trip_planner.next_available_trip()

    def _create_map(self):
        geographical_map = folium.Map(
            location=[self.next_trip["lat"].mean(), self.next_trip["lon"].mean()],
            zoom_start=5,
        )

        for _, row in self.next_trip.iterrows():
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=f"{row['name']}<br>{row['time']}<br>{row['date']}",
            ).add_to(geographical_map)
        
        return geographical_map
    
    def display_map(self):
        st.markdown("## Karta över stationerna i din resa")
        desc = st.container(border=True)
        desc.markdown("Klicka på varje station för mer information. Detta är en exempelresa mellan Malmö och Umeå")
        m = self._create_map()
        map_html = m._repr_html_()
        styled_html = f"""
        <div style="border: 5px solid #20265A; border-radius: 3px; ">
            {map_html}
        </div>
        """
        st.components.v1.html(styled_html, height = 500)

