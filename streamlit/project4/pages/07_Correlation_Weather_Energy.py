# streamlit/Prosject4/07_Correlation_Weather_Energy.py
 
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from utils.utils import initialize_session_state
from utils.data_loaders import load_mongoDB, load_all_era5_data

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
df_prod = load_mongoDB(MONGO_COLLECTION_PRODUCTION, MONGO_DATABASE)
df_cons = load_mongoDB(MONGO_COLLECTION_CONSUMPTION, MONGO_DATABASE)

df_energy = df_prod.copy() if st.session_state.selected_energy_datatype == "Production data" else df_cons.copy()

# Short-circuit if selection not locked
if not st.session_state.filtering_confirmed:
    st.error("Please configure the Area on the Home page first.")
    st.stop()

# ensure datetime index
if "time" in df_weather.columns:
    df_weather["time"] = pd.to_datetime(df_weather["time"]).dt.tz_localize(None)
    df_weather.set_index("time", inplace=True)
else:
    df_weather.index = pd.to_datetime(df_weather.index).tz_localize(None)

if "time" in df_energy.columns:
    df_energy["time"] = pd.to_datetime(df_energy["time"]).dt.tz_localize(None)
    df_energy.set_index("time", inplace=True)
else:
    df_energy.index = pd.to_datetime(df_energy.index).tz_localize(None)

# Filter area
df_weather = df_weather[df_weather["pricearea"] == st.session_state.selected_area].copy()
df_energy = df_energy[df_energy["pricearea"] == st.session_state.selected_area].copy()

# page start
st.subheader(f"Correlation_Weather_Energy in area {st.session_state.selected_area}")

# Date range UI
date_range = st.slider("Select data period", min_value=MIN_DATE, max_value=MAX_DATE, value=[MIN_DATE, MAX_DATE], format="YYYY-MM-DD", key="sarimax_date_range")

start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
end_date = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# draw_analysis_context
st.sidebar.header("Current Selection")
area = st.session_state.get("selected_area", "N/A")
data_type = st.session_state.get("selected_energy_datatype", "N/A")
st.sidebar.info(f"**{area}**")

# Sidebar context
st.sidebar.info(f"**Correlation Analysis:**   {start_date.date()} - {end_date.date()}")

energy_groups = df_energy["groupname"].unique().tolist()
weather_columns = [c for c in df_weather.columns if c != "pricearea" and c != "time"]

# Filter data by start and end date
df_weather_time_filtered = df_weather[(df_weather.index >= start_ts) & (df_weather.index <= end_ts)]
df_weather_time_filtered = df_weather_time_filtered.sort_values(by='time', ascending=True)
df_weather_time_filtered = df_weather_time_filtered.reset_index()

if df_weather_time_filtered.empty:
    st.warning("No weather data found for the selected time window.")
    st.stop()

df_energy_time_filtered = df_energy[(df_energy.index >= start_ts) & (df_energy.index <= end_ts)]
df_energy_time_filtered = df_energy_time_filtered.sort_values(by='time', ascending=True)
df_energy_time_filtered = df_energy_time_filtered.reset_index()

if df_energy_time_filtered.empty:
    st.warning("No energy data found for the selected time window.")
    st.stop()

# widgets
st.markdown("##### Feature and Window Selection")
col_group, col_feature, col_lag, col_window_length, col_center_index = st.columns([1, 1.5, 1, 1, 1.5])

with col_group:
    group_to_analyze = st.selectbox("Energy Sub-Type (Y)", options=energy_groups, index=0, key="energy_group_select")

with col_feature:
    feature_to_analyze = st.selectbox("Weather Feature (X)", options=weather_columns, index=0, key="weather_feature_select")

with col_lag:
    # compute available length safely
    data_len_pre_filter = len(df_energy_time_filtered) // max(1, len(energy_groups))
    max_lag_days = max(0, min(30, (data_len_pre_filter // 24) // 4))
    lag_days = st.slider("Lag (Days)", min_value=0, value=7, max_value=max_lag_days, step=1)
    lag_hours = int(lag_days * 24)
    st.caption(f"Lag steps: {lag_hours} hours")

with col_window_length:
    max_window_days = max(3, min(61, max(3, (data_len_pre_filter // 24) - 1)))
    if max_window_days < 3:
        st.error(f"Not enough hourly data points ({data_len_pre_filter}) for correlation window.")
        st.stop()
    window_days = st.slider("Window Length (Days)", min_value=3, value=7, max_value=max_window_days, step=2)
    window_hours = int(window_days * 24)
    st.caption(f"Window size: {window_hours} hours")

    # Prepare Y and X
    df_energy_group = df_energy_time_filtered[df_energy_time_filtered["groupname"] == group_to_analyze].copy()

    # resample with interpolation (safer than asfreq)
    df_energy_group = df_energy_group.set_index('time')
    df_numeric = df_energy_group.select_dtypes(include=[np.number])
    df_energy_time_filtered = (
        df_numeric
        .resample("H")
        .mean()
        .interpolate(limit=24)
    )

    df_weather_time_filtered = df_weather_time_filtered.set_index('time')
    df_weather_time_filtered = df_weather_time_filtered.asfreq('H')

    DATA_Y = df_energy_group["quantitykwh"].rename(f"{group_to_analyze} Energy Flow")
    DATA_X = df_weather_time_filtered  # full dataframe; lagged correlation function should read column variable

    data_len = len(DATA_Y)
    if DATA_Y.empty or DATA_X.empty or data_len < window_hours:
        st.error(f"No valid data ({data_len} points) available for selected criteria or window is too large.")
        st.stop()

    min_center = window_hours // 2
    max_center = max(0, data_len - window_hours // 2)
    if "center_idx_select" not in st.session_state:
        st.session_state.center_idx_select = data_len // 2
    initial_center = max(min_center, min(st.session_state.center_idx_select, max_center))

with col_center_index:
    if max_center <= min_center:
        st.error("Window size is too large for the dataset.")
        center_idx = min_center
    else:
        center_idx = st.slider("Focus Center Index", min_value=min_center, max_value=max_center, value=initial_center, step=1, key="center_idx_select")

    center_date_display = DATA_Y.index[center_idx].strftime("%Y-%m-%d %H:%M")
    st.caption(f"Center Time: **{center_date_display}**")

st.markdown("---")
st.markdown("##### Correlation Plot")

with st.spinner("Generating lagged correlation plot..."):
    from utils.MachineLearning import lagged_correlation_plot

    fig = lagged_correlation_plot(
        x=DATA_X,
        y=DATA_Y,
        lag=lag_hours,
        window=window_hours,
        center_idx=center_idx,
        variable=feature_to_analyze,
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption(f"Y-Axis (Target): **{group_to_analyze}** | X-Axis (Lagged): **{feature_to_analyze}** | Total Filtered Data Points (Hours): **{data_len}**")
