# streamlit_app/utils/data_loaders.py
import os
import pandas as pd
import streamlit as st
from pymongo import MongoClient
import requests
from typing import Optional, Dict, Any
from typing import List, Dict
from datetime import date
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import streamlit as st

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

FULL_START_DATE = date(2021, 1, 1)
FULL_END_DATE = date(2024, 12, 31)

@st.cache_data(show_spinner=True)
def load_mongoDB(
        collection_name: str, 
        database_name: str
) -> pd.DataFrame:
    """
    load data from remote MongoDB.

    Args:
        collection_name: str
        database_name: str

    Returns:
        pd.DataFrame which contains data collection_name
    """
    mongo_uri = st.secrets["mongo"]["uri"]
    client = MongoClient(mongo_uri)
    db = client[database_name]

    data_cursor = db[collection_name].find({}) 

    data_list = list(data_cursor)
    df = pd.DataFrame(data_list)

    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)

    if 'starttime' in df.columns:
        df['starttime'] = pd.to_datetime(
            df['starttime'], 
            errors='coerce',
            utc=True # Ensure it's read/converted as UTC first
            # infer_datetime_format=True
        ).dt.tz_localize(None)

    if database_name == 'Production database' and 'starttime' in df.columns:
        full_index = pd.date_range(
            start="2021-01-01 00:00:00",
            end="2024-12-31 23:00:00",
            freq="h",
            tz="Europe/Oslo"
        )

        template = pd.DataFrame({"starttime": full_index})

        df_no5_wind = df[(df["pricearea"] == "NO5") & (df["groupname"] == "wind")].copy()

        df_no5_wind_full = template.merge(
            df_no5_wind,
            on="starttime",
            how="left"
        )

        df_no5_wind_full["pricearea"] = "NO5"
        df_no5_wind_full["datatype"]  = "production"
        df_no5_wind_full["groupname"] = "wind"

        df_other = df[
            ~((df["pricearea"] == "NO5") & (df["groupname"] == "wind"))
        ] 

        df = pd.concat([df_other, df_no5_wind_full])

    df = df.set_index('starttime')
    df = df.rename_axis('time')

    client.close()
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

from typing import Optional, Dict, Any
import pandas as pd
import requests
import streamlit as st 

# Note: COORDS_DF, FULL_START_DATE, and FULL_END_DATE 
# are assumed to be defined globally or imported elsewhere.

@st.cache_data(show_spinner=False)
def get_era5_data_for_coords(
    latitude: float,
    longitude: float,
    area_name: str 
) -> Optional[pd.DataFrame]:
    """
    Get historical ERA5 weather data from Open-Meteo API for a specific coordinate pair.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        area_name (str): The name of the price area (e.g., "NO3").

    Returns:
        pd.DataFrame or None: Hourly weather data with the 'pricearea' column added, 
                              or None if request fails.
    """
    BASE_URL = "https://archive-api.open-meteo.com/v1/era5"
    
    # Define API parameters
    params: Dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
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
        "start_date": FULL_START_DATE, 
        "end_date": FULL_END_DATE,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error fetching data for area {area_name} ({latitude}, {longitude}): {e}")
        return None

    hourly_data = data.get("hourly")
    if not hourly_data or 'time' not in hourly_data:
        st.warning(f"No valid hourly data returned for area {area_name}") 
        return None

    # --- Pandas Cleanup ---
    df = pd.DataFrame(hourly_data)
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(
            df['time'], 
            errors='coerce',
            utc=True 
        ).dt.tz_localize(None)

    # Add the area name before setting the index
    df['pricearea'] = area_name
    
    df = df.set_index("time").dropna()
    # ----------------------

    return df

@st.cache_data(show_spinner=True)
def load_all_era5_data(coords_df: pd.DataFrame) -> pd.DataFrame: # Explicitly return pd.DataFrame
    """
    Load ERA5 data for ALL price areas defined in coords_df and combines them
    into a single DataFrame.

    Args:
        coords_df (pd.DataFrame): DataFrame mapping 'pricearea' to coordinates.

    Returns:
        pd.DataFrame: A single DataFrame containing all ERA5 data for all areas.
    """

    all_dfs = []
    
    # Loop through every row in the coordinate map
    for area, row in coords_df.iterrows():
        try:
            latitude = row['lat']
            longitude = row['lon']
            
            # Call the function to fetch data
            df_area = get_era5_data_for_coords(
                latitude=latitude, 
                longitude=longitude, 
                area_name=area
            )
            
            if df_area is not None:
                all_dfs.append(df_area)
                
        except KeyError as e:
            st.error(f"Missing column or index data in COORDS_DF: {e}")
            continue
            
    # Concatenate all individual DataFrames into one
    if all_dfs:
        final_df = pd.concat(all_dfs)
        return final_df
    else:
        # If loading failed, return an empty DataFrame
        st.error(f"Failed to load data for any area.")
        empty_df = pd.DataFrame()
        return empty_df