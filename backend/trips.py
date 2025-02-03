import osmnx as ox
import folium
import requests
import networkx as nx
import geopandas as gpd
from geopy.distance import geodesic
from shapely.geometry import LineString, Point
from backend.connect_to_api import ResRobot
from polyline import decode

class TripPlanner:
    def __init__(self, origin_id: str, destination_id: str):
        self.resrobot = ResRobot()
        self.origin_id = origin_id
        self.destination_id = destination_id
        self.trip_data = self.resrobot.trips(origin_id, destination_id)
        self.route_legs = []
        self.map_route = None

    def extract_route_with_transfers(self):
        if "Trip" in self.trip_data and self.trip_data["Trip"]:
            first_trip = self.trip_data["Trip"][0]
            legs = first_trip["LegList"].get("Leg", [])
            if isinstance(legs, dict):
                legs = [legs]
            for leg in legs:
                transport_type = leg.get("Product", [{}])[0].get("catCode", "unknown")
                origin = leg["Origin"]
                destination = leg["Destination"]
                stops = leg.get("Stops", {}).get("Stop", [])
                if isinstance(stops, dict):
                    stops = [stops]
                segment_stations = [
                    (origin["extId"], origin["lat"], origin["lon"], origin["name"])
                ] + [
                    (stop["extId"], stop["lat"], stop["lon"], stop["name"]) for stop in stops
                ] + [
                    (destination["extId"], destination["lat"], destination["lon"], destination["name"])
                ]
                self.route_legs.append((transport_type, segment_stations))
        return self.route_legs

    def initialize_map(self):
        map_center = [self.route_legs[0][1][0][1], self.route_legs[0][1][0][2]]
        self.map_route = folium.Map(location=map_center, zoom_start=10)

    def plot_train_routes(self, train_stations):
        """Plots train routes using railway data from OSM."""

        for i in range(len(train_stations) - 1):
            start_id, start_lat, start_lon, start_name = train_stations[i]
            end_id, end_lat, end_lon, end_name = train_stations[i + 1]

            # 🔍 **Print for Debugging**
            print(f"🛤️ Processing Segment {i}: {start_name} ({start_lat}, {start_lon}) → {end_name} ({end_lat}, {end_lon})")

            # ✅ Check if any station is missing lat/lon values
            if None in [start_lat, start_lon, end_lat, end_lon]:
                print(f"🚨 Skipping segment {i}: Missing coordinates for {start_name} or {end_name}")
                continue

            # ✅ Check if it's trying to plot a duplicate station
            if (start_lat, start_lon) == (end_lat, end_lon):
                print(f"⚠️ Skipping segment {i}: Start and end stations are the same ({start_name})")
                continue

            # ✅ Ensure a minimum buffer size
            segment_distance = Point(start_lon, start_lat).distance(Point(end_lon, end_lat))
            buffer_size = max(0.005, min(0.15, segment_distance * 0.02))

            polyline = LineString([(start_lon, start_lat), (end_lon, end_lat)])
            buffered_polyline = polyline.buffer(buffer_size)

            print(f"🚆 Querying railway paths with buffer {buffer_size:.4f} degrees.")

            try:
                railways = ox.features_from_polygon(buffered_polyline, tags={"railway": "rail"})
            except Exception as e:
                print(f"⚠️ Error fetching railway data: {e}")
                continue  # Skip if the query fails

            # ✅ Build Graph (Ensure fully connected components)
            G = nx.Graph()
            for _, row in railways.iterrows():
                if row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    for j in range(len(coords) - 1):
                        lon1, lat1 = coords[j]
                        lon2, lat2 = coords[j+1]
                        dist = Point(lon1, lat1).distance(Point(lon2, lat2))
                        G.add_edge((lon1, lat1), (lon2, lat2), weight=dist)

            if G.number_of_nodes() == 0:
                print(f"🚨 No railway data found for segment {i}.")
                continue

            # ✅ Find the **largest connected component** (to prevent disjoint paths)
            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()

            try:
                # ✅ Find nearest nodes and check connectivity
                start_node = min(G.nodes, key=lambda node: Point(node).distance(Point(start_lon, start_lat)))
                end_node = min(G.nodes, key=lambda node: Point(node).distance(Point(end_lon, end_lat)))

                if nx.has_path(G, start_node, end_node):
                    route = nx.shortest_path(G, start_node, end_node, weight="weight")
                    route_coords = [(lat, lon) for lon, lat in route]  # ✅ Ensure correct coordinate format

                    # ✅ Plot the train route in **consistent blue**
                    folium.PolyLine(route_coords, color="blue", weight=5, opacity=1, tooltip="Train Route").add_to(self.map_route)
                    print(f"✅ Successfully plotted train segment {i}")

                else:
                    print(f"🚨 No connected railway path found! Skipping segment {i}")

            except nx.NetworkXNoPath:
                print(f"🚨 No railway path found between ({start_lat}, {start_lon}) and ({end_lat}, {end_lon})")


    def plot_long_distance_train_routes(self, train_stations):
        """Plots long-distance train routes using railway data from OSM without forced switching."""
        
        stations = {stop[0]: (stop[1], stop[2], stop[3]) for stop in train_stations}

        for i in range(len(train_stations) - 1):
            start_lat, start_lon, _ = stations[train_stations[i][0]]
            end_lat, end_lon, _ = stations[train_stations[i + 1][0]]

            # ✅ Dynamically adjust buffer size based on segment distance
            segment_distance = Point(start_lon, start_lat).distance(Point(end_lon, end_lat))
            buffer_size = min(0.20, segment_distance * 0.05)  # Increased max buffer for long distances

            polyline = LineString([(start_lon, start_lat), (end_lon, end_lat)])
            buffered_polyline = polyline.buffer(buffer_size)

            print(f"🚄 Querying long-distance railway paths with buffer {buffer_size:.4f} degrees.")

            try:
                railways = ox.features_from_polygon(buffered_polyline, tags={"railway": "rail"})
            except Exception as e:
                print(f"⚠️ Error fetching railway data: {e}")
                continue  # Skip if the query fails

            # ✅ Build Graph (Ensure fully connected components)
            G = nx.Graph()
            for _, row in railways.iterrows():
                if row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    for j in range(len(coords) - 1):
                        lon1, lat1 = coords[j]
                        lon2, lat2 = coords[j+1]
                        dist = Point(lon1, lat1).distance(Point(lon2, lat2))
                        G.add_edge((lon1, lat1), (lon2, lat2), weight=dist)

            if G.number_of_nodes() == 0:
                print(f"🚨 No railway data found for segment {i}. Skipping.")
                continue

            # ✅ Find the **largest connected component** (to prevent disjoint paths)
            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()

            try:
                # ✅ Find nearest nodes and check connectivity
                start_node = min(G.nodes, key=lambda node: Point(node).distance(Point(start_lon, start_lat)))
                end_node = min(G.nodes, key=lambda node: Point(node).distance(Point(end_lon, end_lat)))

                if nx.has_path(G, start_node, end_node):
                    route = nx.shortest_path(G, start_node, end_node, weight="weight")
                    route_coords = [(lat, lon) for lon, lat in route]  # ✅ Ensure correct coordinate format

                    # ✅ Plot the train route in **consistent dark blue**
                    folium.PolyLine(route_coords, color="darkblue", weight=5, opacity=1, tooltip="Long-Distance Train Route").add_to(self.map_route)
                    print(f"✅ Successfully plotted long-distance train segment {i}")

                else:
                    print(f"🚨 No connected railway path found! Skipping segment {i}")

            except nx.NetworkXNoPath:
                print(f"🚨 No railway path found between ({start_lat}, {start_lon}) and ({end_lat}, {end_lon})")

            # ✅ Plot Start & End Train Stations
            folium.Marker([start_lat, start_lon], popup=f"Train Station {i}", icon=folium.Icon(color="darkblue")).add_to(self.map_route)
            folium.Marker([end_lat, end_lon], popup=f"Train Station {i+1}", icon=folium.Icon(color="darkblue")).add_to(self.map_route)
        
        print("✅ Long-distance train routes plotted successfully!")

    def plot_road_routes(self, road_stations):
            """Plots road routes using OSRM instead of OSMNx querying."""

            stations = {stop[0]: (stop[1], stop[2], stop[3]) for stop in road_stations}

            for i in range(len(road_stations) - 1):
                start = (stations[road_stations[i][0]][0], stations[road_stations[i][0]][1])
                end = (stations[road_stations[i + 1][0]][0], stations[road_stations[i + 1][0]][1])

                # ✅ OSRM Routing API URL
                osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full"

                print(f"📡 Requesting OSRM route: {start} → {end}")
                response = requests.get(osrm_url)

                # ✅ Check if request was successful
                if response.status_code != 200:
                    print(f"❌ OSRM Request Failed! HTTP {response.status_code}")
                    continue  # Skip this segment if the request fails

                data = response.json()

                # ✅ Extract and decode the Polyline
                try:
                    if "routes" in data and data["routes"]:
                        encoded_polyline = data["routes"][0]["geometry"]
                        route_coords = decode(encoded_polyline)  # Decode Polyline into (lat, lon) points
                        print(f"✅ Found OSRM route with {len(route_coords)} points!")
                    else:
                        print(f"❌ No valid route found by OSRM for segment {i}")
                        continue  # Skip to the next segment if no route is found
                except KeyError:
                    print(f"❌ Unexpected OSRM response format! Skipping segment {i}")
                    continue

                # ✅ Plot Start & End Markers
                folium.Marker(start, popup=f"Stop {i}", icon=folium.Icon(color="green")).add_to(self.map_route)
                folium.Marker(end, popup=f"Stop {i+1}", icon=folium.Icon(color="red")).add_to(self.map_route)

                # ✅ Plot the OSRM route in Red
                folium.PolyLine(route_coords, color="red", weight=5, opacity=0.8, tooltip=f"Road Route {i}-{i+1}").add_to(self.map_route)

                print(f"✅ Successfully plotted segment {i} on the map!\n")
    def plot_tram_routes(self, tram_stations):
        """Plots tram routes using OSM tramway data with better path accuracy."""
        
        stations = {stop[0]: (stop[1], stop[2], stop[3]) for stop in tram_stations}

        for i in range(len(tram_stations) - 1):
            start_lat, start_lon, _ = stations[tram_stations[i][0]]
            end_lat, end_lon, _ = stations[tram_stations[i + 1][0]]

            buffer_size = 0.005  # Approx 500m buffer

            polyline = LineString([(start_lon, start_lat), (end_lon, end_lat)])
            buffered_polyline = polyline.buffer(buffer_size)

            print(f"\U0001F68B Querying tram paths with buffer {buffer_size:.4f} degrees.")

            try:
                tram_data = ox.features_from_polygon(buffered_polyline, tags={"railway": "tram"})
            except Exception as e:
                print(f"⚠️ Error fetching tramway data: {e}")
                continue

            if tram_data.empty:
                print(f"❌ No tram paths found for tram segment {i}. Trying fallback expansion...")
                buffer_size *= 2
                buffered_polyline = polyline.buffer(buffer_size)
                try:
                    tram_data = ox.features_from_polygon(buffered_polyline, tags={"railway": "tram"})
                except:
                    continue

                if tram_data.empty:
                    print(f"❌ No tram paths found even after expansion. Skipping segment {i}.")
                    continue

            G = nx.Graph()
            for _, row in tram_data.iterrows():
                if row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    for j in range(len(coords) - 1):
                        lon1, lat1 = coords[j]
                        lon2, lat2 = coords[j + 1]
                        dist = Point(lon1, lat1).distance(Point(lon2, lat2))
                        G.add_edge((lon1, lat1), (lon2, lat2), weight=dist)

            if G.number_of_nodes() == 0:
                print(f"🚨 No connected tramways found for segment {i}.")
                continue

            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()

            try:
                start_node = min(G.nodes, key=lambda node: Point(node).distance(Point(start_lon, start_lat)))
                end_node = min(G.nodes, key=lambda node: Point(node).distance(Point(end_lon, end_lat)))

                if nx.has_path(G, start_node, end_node):
                    route = nx.shortest_path(G, start_node, end_node, weight="weight")
                    route_coords = [(lat, lon) for lon, lat in route]

                    folium.PolyLine(route_coords, color="purple", weight=5, opacity=0.8, tooltip="Tram Route").add_to(self.map_route)
                    print(f"✅ Successfully plotted tram segment {i}")
                else:
                    print(f"🚨 No connected tramway path found! Skipping segment {i}")

            except nx.NetworkXNoPath:
                print(f"🚨 No tramway path found between ({start_lat}, {start_lon}) and ({end_lat}, {end_lon})")

            folium.Marker([start_lat, start_lon], popup=f"Tram Stop {i}", icon=folium.Icon(color="purple")).add_to(self.map_route)
            folium.Marker([end_lat, end_lon], popup=f"Tram Stop {i+1}", icon=folium.Icon(color="purple")).add_to(self.map_route)
        
        print("✅ Tram routes plotted successfully!")
    def plot_subway_routes(self, subway_stations):
        """Plots subway (metro) routes using OSM data with optimal pathing."""
        
        stations = {stop[0]: (stop[1], stop[2], stop[3]) for stop in subway_stations}

        for i in range(len(subway_stations) - 1):
            start_lat, start_lon, _ = stations[subway_stations[i][0]]
            end_lat, end_lon, _ = stations[subway_stations[i + 1][0]]

            buffer_size = 0.008  # Approx 800m buffer (since subways curve underground)

            polyline = LineString([(start_lon, start_lat), (end_lon, end_lat)])
            buffered_polyline = polyline.buffer(buffer_size)

            print(f"\U0001F687 Querying subway paths with buffer {buffer_size:.4f} degrees.")

            try:
                subway_data = ox.features_from_polygon(buffered_polyline, tags={"railway": "subway"})
            except Exception as e:
                print(f"⚠️ Error fetching subway data: {e}")
                continue

            if subway_data.empty:
                print(f"❌ No subway paths found for segment {i}. Expanding buffer...")
                buffer_size *= 2
                buffered_polyline = polyline.buffer(buffer_size)

                try:
                    subway_data = ox.features_from_polygon(buffered_polyline, tags={"railway": "subway"})
                except:
                    continue

                if subway_data.empty:
                    print(f"❌ No subway paths found after expansion. Skipping segment {i}.")
                    continue

            G = nx.Graph()
            for _, row in subway_data.iterrows():
                if row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    for j in range(len(coords) - 1):
                        lon1, lat1 = coords[j]
                        lon2, lat2 = coords[j + 1]
                        dist = Point(lon1, lat1).distance(Point(lon2, lat2))
                        G.add_edge((lon1, lat1), (lon2, lat2), weight=dist)

            if G.number_of_nodes() == 0:
                print(f"\U0001F6A8 No connected subway tracks found for segment {i}.")
                continue

            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()

            try:
                start_node = min(G.nodes, key=lambda node: Point(node).distance(Point(start_lon, start_lat)))
                end_node = min(G.nodes, key=lambda node: Point(node).distance(Point(end_lon, end_lat)))

                if nx.has_path(G, start_node, end_node):
                    route = nx.shortest_path(G, start_node, end_node, weight="weight")
                    route_coords = [(lat, lon) for lon, lat in route]

                    folium.PolyLine(route_coords, color="darkblue", weight=5, opacity=0.8, tooltip="Subway Route").add_to(self.map_route)
                    print(f"✅ Successfully plotted subway segment {i}")
                else:
                    print(f"\U0001F6A8 No connected subway path found! Skipping segment {i}")

            except nx.NetworkXNoPath:
                print(f"\U0001F6A8 No subway path found between ({start_lat}, {start_lon}) and ({end_lat}, {end_lon})")

            folium.Marker([start_lat, start_lon], popup=f"Subway Stop {i}", icon=folium.Icon(color="darkblue")).add_to(self.map_route)
            folium.Marker([end_lat, end_lon], popup=f"Subway Stop {i+1}", icon=folium.Icon(color="darkblue")).add_to(self.map_route)
        
        print("✅ Subway routes plotted successfully!")

    def plot_walking_route(self, start, end):
        """Plots the shortest walking path using a combined OSM pedestrian network."""
        if start == end:
            print(f"🚶 Skipping walking path: Start and end locations are the same {start}")
            return

        polyline = LineString([(start[1], start[0]), (end[1], end[0])])
        buffered_polyline = polyline.buffer(0.005)

        print(f"🚶 Walking from {start} to {end}")
        
        pedestrian_tags = {
            "highway": ["footway", "pedestrian", "path", "track"],
            "sidewalk": "yes",
            "access": ["permissive", "yes"]
        }

        try:
            walking_features = ox.features_from_polygon(buffered_polyline, tags=pedestrian_tags)

            if walking_features is None or len(walking_features) == 0:
                print(f"🚨 No pedestrian paths found between {start} and {end}")
                return

            print(f"✅ Found {len(walking_features)} pedestrian paths. Combining networks...")

            G = nx.Graph()
            for _, row in walking_features.iterrows():
                if row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    for i in range(len(coords) - 1):
                        lat1, lon1 = coords[i][1], coords[i][0]
                        lat2, lon2 = coords[i + 1][1], coords[i + 1][0]
                        dist = LineString([coords[i], coords[i + 1]]).length
                        G.add_edge((lat1, lon1), (lat2, lon2), weight=dist)

            start_node = min(G.nodes, key=lambda node: LineString([node, start]).length)
            end_node = min(G.nodes, key=lambda node: LineString([node, end]).length)

            if start_node == end_node:
                print(f"🚶 Skipping walking path: Nearest nodes are the same {start_node}")
                return

            print(f"🔎 Found nearest nodes: {start_node} -> {end_node}")

            route = nx.shortest_path(G, start_node, end_node, weight="weight")
            route_coords = [(node[0], node[1]) for node in route]

            folium.PolyLine(route_coords, color="green", weight=5, opacity=1, tooltip="Walking Route").add_to(self.map_route)
            print(f"✅ Walking path plotted from {start} to {end}")

        except Exception as e:
            print(f"🚨 Error processing walking path: {e}")

    def plot_trip(self):
        self.initialize_map()
        for transport_type, stations in self.route_legs:
            if transport_type == "4":
                self.plot_train_routes(stations)
            elif transport_type in ["2", "7"]:
                self.plot_road_routes(stations)
            elif transport_type == "3":
                self.plot_long_distance_train_routes(stations)
            elif transport_type == "6":
                self.plot_tram_routes(stations)
            elif transport_type == "5":
                self.plot_subway_routes(stations)
            elif transport_type == "unknown" and len(self.route_legs) > 1:
                start = self.route_legs[-2][1][-1][1:3]
                end = stations[-1][1:3]
                self.plot_walking_route(start, end)
        
        # ✅ Add station markers
        for _, stations in self.route_legs:
            for stop in stations:
                folium.Marker(
                    location=[stop[1], stop[2]], 
                    popup=stop[3], 
                    icon=folium.Icon(color="green")
                ).add_to(self.map_route)
                
        return self.map_route

if __name__ == "__main__":
    planner = TripPlanner("740000014", "740000480")
    planner.extract_route_with_transfers()
    trip_map = planner.plot_trip()
    trip_map
    
    
    # Stockholm > 
# 740000001,Stockholm Centralstation
# 740021691,Skarpnäck T-bana,
# 740021692,Bagarmossen T-bana,
# 740021693,Kärrtorp T-bana,
# 740011606,Tekniska Högskolan
# Göteborg  >
# 740000002,Göteborg Centralstation
# 740025715 Mölndal lackarebäck
# 740059809 Mölndal bifrost
# 740060697 Orust ridklubb
# 740000098 Ljungskile
# Stenungsund Station 740000014
# Uddevalla Kampenhof 740000480
# 🎯 **Fetch Real-Time Stops from ResRobot**
