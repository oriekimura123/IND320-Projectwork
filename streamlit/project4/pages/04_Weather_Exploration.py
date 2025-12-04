# streamlit/Project4/pages/04_Weather_Exploration.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, time
from utils.utils import initialize_session_state
from utils.data_loaders import load_all_era5_data, load_mongoDB

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
st.subheader(f"Weather data exploration area {st.session_state.selected_area}")

# Select data period
date_range = st.slider("Select Date Range", min_value=MIN_DATE, max_value=MAX_DATE, value=[MIN_DATE, MAX_DATE], format="YYYY-MM-DD", key="weather_date_range")

start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# draw_analysis_context
st.sidebar.header("Current Selection")
area = st.session_state.get("selected_area", "N/A")
data_type = st.session_state.get("selected_energy_datatype", "N/A")
st.sidebar.info(f"**{area}**")

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

# Filter data by start and end date
df_time_filtered = df_weather[(df_weather.index >= start_ts) & (df_weather.index <= end_ts)]
df_time_filtered = df_time_filtered.sort_values(by='time', ascending=True)
df_time_filtered = df_time_filtered.reset_index()

if df_time_filtered.empty:
    st.warning("No data found for the selected time window.")
    st.stop()

# Display selection
chart_columns = [col for col in df_time_filtered.columns if col != "time" and col != "pricearea"]

selected_column = st.selectbox("Metric to Display (Line Plot)", ["All Columns"] + chart_columns, key="metric_selector", width=200)

def min_max_normalize(series: pd.Series):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return series - min_val
    return (series - min_val) / (max_val - min_val)

display_data_weather = df_time_filtered.copy()

if selected_column == "All Columns":
    df_normalized = display_data_weather.copy()
    for col in chart_columns:
        if col != "pricearea":
            df_normalized[col] = min_max_normalize(df_normalized[col])
    # df_normalized = df_normalized.reset_index(names=["time"])
    df_long = df_normalized.melt(id_vars="time", value_vars=chart_columns, var_name="Metric", value_name="Normalized Value")
    fig = px.line(df_long, x="time", y="Normalized Value", color="Metric", title=f"All Metrics (Normalized) - {start_date.date()} to {end_date.date()}", labels={"Normalized Value": "Normalized Value (0 to 1)", "time": "Date"})
    st.caption("All metrics have been scaled (0 to 1) to allow comparison of relative trends.")
else:
    fig = px.line(display_data_weather.reset_index(), x="time", y=selected_column, title=f"Observation for {selected_column} - {start_date.date()} to {end_date.date()}", labels={selected_column: selected_column, "time": "Date"})

fig.update_layout(xaxis_title="Date", hovermode="x unified", title=dict(font=dict(size=24)), margin=dict(l=20, r=20, t=60, b=20))
st.plotly_chart(fig, use_container_width=True)

