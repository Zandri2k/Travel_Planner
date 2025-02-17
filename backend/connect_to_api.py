from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


class ResRobot:
    API_KEY = st.secrets["api"]["API_KEY"]  # ResRobot2.1
    API_KEY2 = st.secrets["api"]["API_KEY2"]  # Traffikverket öppet API
    API_KEY3 = st.secrets["api"]["API_KEY3"]  # GTFS Sverige2
    API_KEY4 = st.secrets["api"]["API_KEY4"]  # GTFS Regional Static data
    API_KEY5 = st.secrets["api"]["API_KEY5"]  # GTFS3
    API_KEY6 = st.secrets["api"]["API_KEY6"]  # GoogleMaps

    def trips(
        self,
        origin_id=740000001,
        destination_id=740098001,
        date=None,
        time=None,
        searchForArrival=0,
    ):
        """Retrieve trip details including all intermediate stops.

        Parameters:
          origin_id:   Stop id for origin.
          destination_id:  Stop id for destination.
          date:        Date in YYYY-MM-DD format (defaults to today).
          time:        Time in HH:MM format (defaults to now).
          searchForArrival: 0 to search for departures, 1 for arrivals.
        """
        if date is None:
            date = datetime.today().strftime("%Y-%m-%d")
        if time is None:
            time = datetime.now().strftime("%H:%M")

        url = (
            f"https://api.resrobot.se/v2.1/trip?format=json"
            f"&originId={origin_id}&destId={destination_id}"
            f"&passlist=true&showPassingPoints=true"
            f"&date={date}&time={time}"
            f"&searchForArrival={searchForArrival}"
            f"&accessId={self.API_KEY}"
        )

        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            print(f"Network or HTTP error: {err}")
            return None

    def access_id_from_location(self, location):
        """Look up stop IDs based on a location name."""
        url = f"https://api.resrobot.se/v2.1/location.name?input={location}&format=json&accessId={self.API_KEY}"
        response = requests.get(url)
        result = response.json()

        print(f"{'Name':<40} {'extId':<12} {'Latitude':<12} {'Longitude'}")
        print("-" * 80)

        for stop in result.get("stopLocationOrCoordLocation", []):
            stop_data = next(iter(stop.values()))
            stop_name = stop_data.get("name", "Unknown")
            stop_id = stop_data.get("extId", "N/A")
            lat = stop_data.get("lat", "N/A")
            lon = stop_data.get("lon", "N/A")

            print(f"{stop_name:<40} {stop_id:<12} {lat:<12} {lon}")

    def timetable_departure(self, location_id=740015565):
        """Get the departure board for a given location."""
        url = f"https://api.resrobot.se/v2.1/departureBoard?id={location_id}&format=json&accessId={self.API_KEY}&passlist=1"  # noqa: E501

        response = requests.get(url)
        return response.json()

    def timetable_arrival(self, location_id=740015565):
        """Get the arrival board for a given location."""
        url = f"https://api.resrobot.se/v2.1/arrivalBoard?id={location_id}&format=json&accessId={self.API_KEY}"
        response = requests.get(url)
        return response.json()

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

    def name_from_access_id(self, ext_id):
        """
        Fetch the name of a location given its extId.

        Parameters:
        ----------
        ext_id : int or str
            The unique identifier (extId) of the location.

        Returns:
        -------
        str
            The name of the location, or None if not found.
        """
        url = f"https://api.resrobot.se/v2.1/location.name?input={ext_id}&format=json&accessId={self.API_KEY}"

        try:
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            for stop in data.get("stopLocationOrCoordLocation", []):
                stop_data = next(iter(stop.values()))
                if str(stop_data.get("extId")) == str(ext_id):
                    return stop_data.get("name")
            return None  # Return None if no matching extId is found
        except requests.exceptions.RequestException as err:
            print(f"Error fetching name for extId {ext_id}: {err}")
            return None

    def nearby_stops2(self, latitude, longitude, max_results=10):
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
