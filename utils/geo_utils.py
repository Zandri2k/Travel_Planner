import numpy as np

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the Haversine distance between two points."""
    R = 6371  # Earth radius in kilometers
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def filter_stops_within_radius(stops_df, center_lat, center_lon, radius_km=150):
    """Filter stops within a given radius from the center point."""
    stops_df["distance"] = stops_df.apply(
        lambda row: haversine(center_lat, center_lon, row["stop_lat"], row["stop_lon"]), axis=1
    )
    return stops_df[stops_df["distance"] <= radius_km]["stop_name"].tolist()

def calculate_midpoint(lat1, lon1, lat2, lon2):
    """Calculate the midpoint between two coordinates."""
    return (lat1 + lat2) / 2, (lon1 + lon2) / 2

def calculate_zoom_level(lat1, lon1, lat2, lon2):
    """Calculate the zoom level for the map based on the distance between two points."""
    distance = haversine(lat1, lon1, lat2, lon2)
    if distance > 100:
        return 8
    elif distance > 50:
        return 9
    elif distance > 20:
        return 10
    elif distance > 10:
        return 11
    else:
        return 12

def interpolate_points(route_coords, num_points=200):
    """Interpolate points between route coordinates for smoother curves."""
    lats = np.array([coord[0] for coord in route_coords])
    lons = np.array([coord[1] for coord in route_coords])
    distances = np.cumsum(np.sqrt(np.ediff1d(lats, to_begin=0)**2 + np.ediff1d(lons, to_begin=0)**2))
    distances = distances / distances[-1]
    interpolated_lats = np.interp(np.linspace(0, 1, num_points), distances, lats)
    interpolated_lons = np.interp(np.linspace(0, 1, num_points), distances, lons)
    return list(zip(interpolated_lats, interpolated_lons))
