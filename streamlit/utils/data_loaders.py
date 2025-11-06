# streamlit_app/utils/data_loaders.py
import os
import pandas as pd
import streamlit as st
from pymongo import MongoClient

import requests
from typing import Optional, Dict, Any

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

@st.cache_data(show_spinner=False)
def get_meteo_csv(filename: str) -> pd.DataFrame:
    """
    load data from csv file.

    Args:
        filename: str

    Returns:
        pd.DataFrame which contains data file_name
    """
    filepath = os.path.join(DATA_DIR, filename)
    try:
        df = pd.read_csv(filepath)
        return df
    except FileNotFoundError:
        st.error(f"File not found: {filepath}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_mongoDB(collection_name: str, database_name: str) -> pd.DataFrame:
    """
    load data from remote MongoDB.

    Args:
        collection_name: str
        database_name: str

    Returns:
        pd.DataFrame which contains data collection_name:.database_name
    """
    mongo_uri = st.secrets["mongo"]["uri"]
    client = MongoClient(mongo_uri)
    db = client[database_name]
    df = pd.DataFrame(list(db[collection_name].find()))
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)
    return df

# Define pricearea, lon and lat
city_data = {
    "pricearea": ["NO1", "NO2", "NO3", "NO4", "NO5"],
    "city_names": ["Oslo", "Kristiansand", "Trondheim", "Tromsø", "Bergen"],
    "lon": [10.7461, 7.9956, 10.3951, 18.957, 5.328],
    "lat": [59.9127, 58.1467, 63.4305, 69.6496, 60.392],
}

COORDS_DF = pd.DataFrame(city_data)
COORDS_DF = COORDS_DF.set_index('pricearea')

@st.cache_data(show_spinner=False)
def get_era5_data(latitude: float, longitude: float, year: str) -> Optional[pd.DataFrame]:
    """
    Get historical ERA5 weather data from Open-Meteo API.

    Args:
        latitude (float): Latitude coordinate (e.g., 52.52).
        longitude (float): Longitude coordinate (e.g., 13.41).
        year (str): Year in 'YYYY' format (e.g., '2019').

    Returns:
        pd.DataFrame or None: Hourly weather data, or None if request fails.
    """
    BASE_URL = "https://archive-api.open-meteo.com/v1/era5"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": [
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_gusts_10m",
            "wind_direction_10m",
        ],
        "timezone": "auto",
        "models": "era5",
        "wind_speed_unit": "ms",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f" Error fetching data for ({latitude}, {longitude}): {e}")
        return None

    hourly_data = data.get("hourly")
    if not hourly_data:
        print(f" No hourly data returned for ({latitude}, {longitude})")
        return None

    df = pd.DataFrame(hourly_data)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.set_index("time")

    return df


def load_era5_data_for_area(area: str, year: str):
    """
    Load ERA5 data for the selected price area and a single year, 
    and stores the resulting single DataFrame.

    Args:
    area: str
    year: str

    """
    # st.info(f"Fetching ERA5 data for **{area}** in **{year}**...")
    
    # Retrieve coordinates and city name from the DataFrame
    try:
        # Use .loc on the index to get the row data
        row = COORDS_DF.loc[area]
        lat = row['lat']
        lon = row['lon']
        city = row['city_names']
    except KeyError:
        st.error(f"Price area '{area}' not found in the coordinate map.")
        # st.session_state['era5_data_raw'] = pd.DataFrame()
        return
        
    # Fetch data by calling the cached function
    df = get_era5_data(lat, lon, year)
    
    if df is not None:
        # Store the single DataFrame in session state
        st.session_state['era5_data_raw'] = df
    else:
        st.error(f"Failed to load data for {year}.")
        st.session_state['era5_data_raw'] = pd.DataFrame()


@st.cache_data(show_spinner=False)
def get_multiple_cities_era5(city_data: Dict[str, Any], year: str) -> Dict[str, pd.DataFrame]:
    """
    Fetch ERA5 weather data for multiple Norwegian price areas.

    Args:
        city_data (dict): Dictionary with price areas, city names, and coordinates.
        year (str): Year to fetch (e.g., '2020').

    Returns:
        dict: {pricearea: DataFrame}
    """
    city_dfs = {}

    for pricearea, city, lat, lon in zip(
        city_data["pricearea"], city_data["city_names"], city_data["lat"], city_data["lon"]
    ):
        # print(f" Fetching ERA5 data for {pricearea} - {city} ({year})...")
        df_city = get_era5_data(lat, lon, year)

        if df_city is not None:
            df_city["pricearea"] = pricearea
            df_city["city"] = city  # optional, if you still want to keep the city name
            city_dfs[pricearea] = df_city
            print(f" Done: {pricearea} ({len(df_city)} records)")
        else:
            print(f" Failed to fetch data for {pricearea} ({city})")

    return city_dfs