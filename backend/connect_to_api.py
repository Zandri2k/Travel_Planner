import os

import requests
from dotenv import load_dotenv

load_dotenv()


class ResRobot:
    API_KEY = os.getenv("API_KEY")  # ResRobot2.1
    API_KEY2 = os.getenv("API_KEY2")  # Traffikverket öppet API
    API_KEY3 = os.getenv("API_KEY3")  # GTFS Sverige2
    API_KEY4 = os.getenv("API_KEY4")  # GTFS Regional Static data
    API_KEY5 = os.getenv("API_KEY5")  # GTFS3
    API_KEY6 = os.getenv("API_KEY6")  # GoogleMaps

    def trips(self, origin_id=740000001, destination_id=740098001):
        """origing_id and destination_id can be found from Stop lookup API"""
        url = f"https://api.resrobot.se/v2.1/trip?format=json&originId={origin_id}&destId={destination_id}&passlist=true&showPassingPoints=true&accessId={self.API_KEY}"  # noqa: E501

        try:
            response = requests.get(url)
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as err:
            print(f"Network or HTTP error: {err}")

    def access_id_from_location(self, location):
        url = f"https://api.resrobot.se/v2.1/location.name?input={location}&format=json&accessId={self.API_KEY}"
        response = requests.get(url)
        result = response.json()

        print(f"{'Name':<50} extId")

        for stop in result.get("stopLocationOrCoordLocation", []):
            stop_data = next(iter(stop.values()))
            stop_name = stop_data.get("name", "Unknown")
            stop_id = stop_data.get("extId", "N/A")
            lat = stop_data.get("lat", "N/A")
            lon = stop_data.get("lon", "N/A")

            # returns None if extId doesn't exist
            if stop_data.get("extId"):
                print(f"{stop_name:<40} {stop_id:<12} {lat:<12} {lon}")

    def timetable_departure(self, location_id=740015565):
        url = f"https://api.resrobot.se/v2.1/departureBoard?id={location_id}&format=json&accessId={self.API_KEY}"
        response = requests.get(url)
        result = response.json()
        return result

    def timetable_arrival(self, location_id=740015565):
        url = f"https://api.resrobot.se/v2.1/arrivalBoard?id={location_id}&format=json&accessId={self.API_KEY}"
        response = requests.get(url)
        result = response.json()
        return result

    def nearby_stops(self, latitude, longitude, max_results=10):
        """
        Fetches nearby public transport stops based on coordinates.

        :param latitude: float - Latitude in decimal degrees (WGS84)
        :param longitude: float - Longitude in decimal degrees (WGS84)
        :param max_results: int - Maximum number of stops to return (default: 10)
        :return: List of nearby stops in JSON format
        """
        url = "https://api.resrobot.se/v2.1/location.nearbystops"
        params = {
            "originCoordLat": latitude,
            "originCoordLong": longitude,
            "maxNo": max_results,  # Number of stops to fetch
            "format": "json",
            "accessId": self.API_KEY,
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            stops = data.get("stopLocationOrCoordLocation", [])

            if not stops:
                print("No nearby stops found.")
                return []

            print(
                f"{'Stop Name':<40} {'Stop ID':<10} {'Latitude':<12} {'Longitude':<12} {'Distance':<10} {'Transport Types'}"  # noqa: E501
            )
            print("-" * 110)

            results = []
            for stop in stops:
                stop_data = stop.get("StopLocation", {})

                stop_name = stop_data.get("name", "Unknown")
                stop_id = stop_data.get("extId", "N/A")
                lat = stop_data.get("lat", "N/A")
                lon = stop_data.get("lon", "N/A")
                distance = stop_data.get(
                    "dist", "N/A"
                )  # Distance from queried location
                transport_types = [
                    p["cls"] for p in stop_data.get("productAtStop", [])
                ]  # Extract transport types

                results.append(
                    {
                        "name": stop_name,
                        "id": stop_id,
                        "lat": lat,
                        "lon": lon,
                        "distance_m": distance,
                        "transport_types": transport_types,
                    }
                )

                print(
                    f"{stop_name:<40} {stop_id:<10} {lat:<12} {lon:<12} {distance:<10} {transport_types}"
                )

            return results

        except requests.exceptions.RequestException as err:
            print(f"Error fetching nearby stops: {err}")
            return []


# resrobot = ResRobot()

# pprint(resrobot.timetable_arrival()["Arrival"][0])
