# streamlit/Prosject4/My_Homepage.py
import sys
import os
import streamlit as st
from pathlib import Path
import datetime
from datetime import date, datetime, timedelta
import folium
from streamlit_folium import st_folium
import json
import pandas as pd
from shapely.geometry import shape, Point
from utils.utils import get_area_filtered_data
from utils.data_loaders import load_mongoDB, load_all_era5_data

# Adds the Root Folder to the search path BEFORE importing from 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Main App Content ---
st.set_page_config(page_title="My Projectwork", layout="wide")
st.subheader("Welcome to My Streamlit App for Projectwork-part4!")
st.write("Orie Kimura, Nov 28, 2025")

@st.cache_data
def load_geojson():
    with open("streamlit/data/price_areas.geojson") as f:
        return json.load(f)

geojson_data = load_geojson()

# Find correct name for area
@st.cache_data
def build_id_to_name(gj):
    out = {}
    for f in gj.get("features", []):
        fid = f.get("id") or (f.get("properties") or {}).get("id")
        if fid is None:
            continue
        name = (f.get("properties") or {}).get("ElSpotOmr")
        if name:
            out[fid] = str(name)
    return out

id_to_name = build_id_to_name(geojson_data)

# Build shapely polygons once (session cache)
if "polygons" not in st.session_state:
    polys = []
    for feat in geojson_data.get("features", []):
        fid = feat.get("id") or (feat.get("properties") or {}).get("id")
        if not fid:
            continue
        try:
            geom = shape(feat["geometry"])
        except Exception:
            continue
        polys.append((fid, geom))
    st.session_state.polygons = polys

def find_feature_id(lon: float, lat: float):
    if shape is None or "polygons" not in st.session_state:
        return None
    pt = Point(lon, lat)  # shapely uses (x,y) = (lon,lat)
    for fid, geom in st.session_state.polygons:
        if geom.covers(pt):  # boundary-inclusive
            return fid
    return None

# Choropleth values (example; replace with real data)
value_map = {6: 5.0, 7: 3.5, 8: 4.2, 9: 6.1, 10: 2.8}
df_vals = pd.DataFrame({"id": list(value_map.keys()), "value": list(value_map.values())})

# Define the full range of data available 
MIN_DATE = date(2021, 1, 1)
MAX_DATE = date(2024, 12, 31)

# Define name of Mongo databae and collections
MONGO_DATABASE = "elhub_data"
MONGO_COLLECTION_PRODUCTION = "production_data_2021_2024"
MONGO_COLLECTION_CONSUMPTION = "consumption_data_2021_2024"

# Define coords_df
city_data = {
    "pricearea": ["NO1", "NO2", "NO3", "NO4", "NO5"],
    "city_names": ["Oslo", "Kristiansand", "Trondheim", "Tromsø", "Bergen"],
    "lon": [10.7461, 7.9956, 10.3951, 18.957, 5.328],
    "lat": [59.9127, 58.1467, 63.4305, 69.6496, 60.392],
}

COORDS_DF = pd.DataFrame(city_data)
## Set the 'pricearea' as the index for efficient lookup
COORDS_DF = COORDS_DF.set_index('pricearea')

# Session state init
if "last_pin" not in st.session_state:
    st.session_state.last_pin = [63.5130, 9.8087]

if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = None

if 'filtering_confirmed' not in st.session_state:
    st.session_state.filtering_confirmed = False
    st.session_state.selected_area = 'NO3' # Default to global scope
    st.session_state.selected_energy_datatype = 'Production data' 
    st.session_state.date_range_1_2 = (MIN_DATE, MAX_DATE)
    st.session_state.date_range_3 = (MIN_DATE, MAX_DATE)


# Preselect 
if st.session_state.selected_feature_id is None:
    lat, lon = st.session_state.last_pin
    st.session_state.selected_feature_id = find_feature_id(lon, lat)

df_weather = load_all_era5_data(COORDS_DF)
df_elhub_production = load_mongoDB(MONGO_COLLECTION_PRODUCTION, MONGO_DATABASE)
df_elhub_consumption = load_mongoDB(MONGO_COLLECTION_CONSUMPTION, MONGO_DATABASE)

# Layout: map left, info right
map_col, info_col = st.columns([2.2, 1])

with map_col:
    # Build map (one per run)
    m = folium.Map(location=st.session_state.last_pin, zoom_start=5, tiles="OpenStreetMap")

    # Choropleth (single layer)
    folium.Choropleth(
        geo_data=geojson_data,
        data=df_vals,
        columns=["id", "value"],
        key_on="feature.id",
        fill_color="YlGnBu",
        fill_opacity=0.4,
        line_opacity=0.8,
        line_color="white",
        legend_name="Value",
        highlight=True
    ).add_to(m)

    # Highlight the selected polygon outline (pre-filtered; no filter_function)
    if st.session_state.selected_feature_id is not None:
        sel_id = st.session_state.selected_feature_id
        sel_feats = [
            f for f in geojson_data.get("features", [])
            if f.get("id") == sel_id or (f.get("properties") or {}).get("id") == sel_id
        ]
        if sel_feats:
            folium.GeoJson(
                {"type": "FeatureCollection", "features": sel_feats},
                style_function=lambda f: {"fillOpacity": 0, "color": "red", "weight": 3},
                name="selection"
            ).add_to(m)

    # Single pin (last clicked)
    folium.Marker(
        location=st.session_state.last_pin,
        icon=folium.Icon(color="red"),
        popup=f"{st.session_state.last_pin[0]:.5f}, {st.session_state.last_pin[1]:.5f}"
    ).add_to(m)

    # Render (width inherits from column)
    out = st_folium(m, key="choropleth_map", height=600, width=None)

    # Process click: update pin and polygon ID, then single rerun
    if out and out.get("last_clicked"):
        lat = out["last_clicked"]["lat"]
        lon = out["last_clicked"]["lng"]
        new_coord = [lat, lon]
        if new_coord != st.session_state.last_pin:
            st.session_state.last_pin = new_coord
            st.session_state.selected_feature_id = find_feature_id(lon, lat)
            st.rerun()

with info_col:
    st.subheader("Area selection")
    st.write(f"Lat: {st.session_state.last_pin[0]:.6f}")
    st.write(f"Lon: {st.session_state.last_pin[1]:.6f}")

    if st.session_state.selected_feature_id is None:
        st.write("Outside known features.")
    else:
        fid = st.session_state.selected_feature_id
        # If your value_map uses int keys and fid is str, this handles both
        try:
            val = value_map.get(fid, value_map.get(int(fid), "n/a"))
        except Exception:
            val = value_map.get(fid, "n/a")
        area_name = id_to_name.get(fid, f"ID {fid}")
        st.write(f"Area: {area_name}")
        st.write(f"Value: {val}")
        st.session_state.proposed_area = "".join(area_name.split())

    st.subheader("Datatype Selection")
    st.session_state.proposed_energy_datatype = st.radio(
        label = "Which type of energy data to analyze?", 
        options=["Production data", "Consumption data"],
        index = 0)

    # --- 3. Confirmation Button ---
    if st.button("Confirm & Lock Selection", 
                disabled=st.session_state.filtering_confirmed):

        # Set state locks
        st.session_state.filtering_confirmed = True
        st.session_state.selected_area = st.session_state.proposed_area
        st.session_state.selected_energy_datatype = st.session_state.proposed_energy_datatype
    
        # Trigger Layer 2 Caching for the selected area
        with st.spinner("Filtering all 3 datasets by area (caching results)..."):
            # Caching runs for the selected area
            get_area_filtered_data(df_elhub_production, st.session_state.selected_area)
            get_area_filtered_data(df_elhub_consumption, st.session_state.selected_area)
            get_area_filtered_data(df_weather, st.session_state.selected_area)
            
        st.sidebar.success("Selection Locked!   \n Data is filtered and cached.")
        st.rerun()

    if st.session_state.filtering_confirmed:
        st.sidebar.success("Selection is locked.   \n **Start analysis!**")
        
        if st.sidebar.button("Reset Selection  \n (Unlock Area/Datatype)"):
            st.session_state.filtering_confirmed = False
            st.rerun()
