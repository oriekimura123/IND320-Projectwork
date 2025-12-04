# streamlit/Prosject4/05_Weather_Outlier.py

import streamlit as st
import pandas as pd
from datetime import date
from utils.utils import initialize_session_state
from utils.data_loaders import load_all_era5_data, load_mongoDB
from utils.spc_analyzer import calculate_SPC_anomalies
from utils.lof_analyzer import analyze_LOF_anomalies

# Constants
MIN_DATE = date(2021, 1, 1)
MAX_DATE = date(2024, 12, 31)
MONGO_DATABASE = "elhub_data"
MONGO_COLLECTION_PRODUCTION = "production_data_2021_2024"
MONGO_COLLECTION_CONSUMPTION = "consumption_data_2021_2024"

# Init session state
initialize_session_state()

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

# Load data (assume these functions are cached)
df_weather = load_all_era5_data(COORDS_DF)
# df_prod = load_mongoDB(MONGO_COLLECTION_PRODUCTION, MONGO_DATABASE)
# df_cons = load_mongoDB(MONGO_COLLECTION_CONSUMPTION, MONGO_DATABASE)

# Short-circuit if selection not locked
if not st.session_state.filtering_confirmed:
    st.error("Please configure the Area on the Home page first.")
    st.stop()

# Date range UI
st.subheader(f"Weather Data Outlier : area : {st.session_state.selected_area}")

# Select data period
date_range = st.slider("Select Date Range", min_value=MIN_DATE, max_value=MAX_DATE, value=[MIN_DATE, MAX_DATE], format="YYYY-MM-DD", key="weather_date_range")

start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# draw_analysis_context
st.sidebar.header("Current Selection")
area = st.session_state.get("selected_area", "N/A")
data_type = st.session_state.get("selected_energy_datatype", "N/A")
st.sidebar.info(f"**{area}, {data_type}**")

# Sidebar context
st.sidebar.info(f"**Weather date range:**  \n {start_date.date()} - {end_date.date()}")

# ensure datetime index
if "time" in df_weather.columns:
    df_weather["time"] = pd.to_datetime(df_weather["time"]).dt.tz_localize(None)
    df_weather.set_index("time", inplace=True)
else:
    df_weather.index = pd.to_datetime(df_weather.index).tz_localize(None)

# Filter area
df_weather = df_weather[df_weather["pricearea"] == st.session_state.selected_area].copy()


# Filtered data
df_time_filtered = df_weather[(df_weather.index >= start_ts) & (df_weather.index <= end_ts)]
df_time_filtered = df_time_filtered.sort_values(by='time', ascending=True)

if df_time_filtered.empty:
    st.warning("No data found for the selected time window.")
    st.stop()

chart_columns = [c for c in df_time_filtered.columns if c != "pricearea" and c != "time"]


tab1, tab2 = st.tabs(["Outlier/SPC analysis", "Anomaly/LOF analysis"])

with tab1:
    feature_to_analyze_SPC = st.selectbox("Type of data", options=chart_columns, index=0, key="spc_feature", width=200)
    SPC_fig, SPC_anomalies = calculate_SPC_anomalies(df_time_filtered, column=feature_to_analyze_SPC)
    st.plotly_chart(SPC_fig, use_container_width=True)
    st.dataframe(SPC_anomalies)

with tab2:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        feature_to_analyze_LOF = st.selectbox("Type of data", options=chart_columns, index=0, key="lof_feature", width=200)
    with col2:
        neighbors = st.slider("Neighbors", min_value=1, value=20, max_value=50, step=1)
    with col3:
        contamination = float(st.slider("Contamination", min_value=0.0, value=0.01, max_value=0.2, step=0.01))

    LOF_fig, LOF_summary, LOF_stats = analyze_LOF_anomalies(df_time_filtered, feature_col=feature_to_analyze_LOF, n_neighbors=int(neighbors), contamination=contamination)
    st.plotly_chart(LOF_fig, use_container_width=True)
    st.write("Statistics:", LOF_stats)
    st.write("Outlier Summary Head:\n", LOF_summary.head())

