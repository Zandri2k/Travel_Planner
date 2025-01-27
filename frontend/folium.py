import folium
import osmnx as ox
import networkx as nx
import numpy as np
import streamlit as st

def create_folium_map(midpoint_lat, midpoint_lon, zoom_level):
    """Create a Folium map centered at the midpoint with the given zoom level."""
    return folium.Map(location=[midpoint_lat, midpoint_lon], zoom_start=zoom_level)

def add_route_to_map(m, route_coords, color="blue", weight=5, opacity=1):
    """Add a route to the Folium map."""
    folium.PolyLine(
        locations=route_coords,
        color=color,
        weight=weight,
        opacity=opacity
    ).add_to(m)

def add_marker_to_map(m, lat, lon, popup_text, icon_color="green"):
    """Add a marker to the Folium map."""
    folium.Marker(
        location=[lat, lon],
        popup=popup_text,
        icon=folium.Icon(color=icon_color)
    ).add_to(m)

def add_small_marker_to_map(m, lat, lon, popup_text):
    """Add a smaller marker to the Folium map."""
    folium.Marker(
        location=[lat, lon],
        popup=popup_text,
        icon=folium.Icon(color="blue", icon="circle", prefix="fa", icon_size=(10, 10))
    ).add_to(m)

def display_map_in_streamlit(m, width=700, height=500):
    """Display the Folium map in Streamlit."""
    folium_html = m._repr_html_()
    st.components.v1.html(folium_html, width=width, height=height)