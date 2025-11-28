# streamlit/Project4/pages/03_Energy_decomposition.py

import streamlit as st
import pandas as pd
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
# df_weather = load_all_era5_data(COORDS_DF)
df_prod = load_mongoDB(MONGO_COLLECTION_PRODUCTION, MONGO_DATABASE)
df_cons = load_mongoDB(MONGO_COLLECTION_CONSUMPTION, MONGO_DATABASE)

# Short-circuit if selection not locked
if not st.session_state.filtering_confirmed:
    st.error("Please configure the Area and type of data on the Home page first.")
    st.stop()

# Date range UI
st.subheader(f"Energy Decomposition area {st.session_state.selected_area}")

col1, col2 = st.columns([1, 3])
with col1:
    selected_datatype = st.radio(
        label = "Datatype Selection", 
        options=["Production data", "Consumption data"],
        index = 0)
    # Select which df to use
    if st.session_state.selected_energy_datatype == "Production data":
        df_energy = df_prod.copy()
    else:
        df_energy = df_cons.copy()
with col2:
    # Select data period
    date_range = st.slider("Select Date Range", min_value=MIN_DATE, max_value=MAX_DATE, value=[MIN_DATE, MAX_DATE], format="YYYY-MM-DD", key="dec_date_range")

    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# draw_analysis_context
st.sidebar.header("Current Selection")
area = st.session_state.get("selected_area", "N/A")
data_type = st.session_state.get("selected_energy_datatype", "N/A")
st.sidebar.info(f"**{area}, {data_type}**")

# Sidebar context
st.sidebar.info(f"**Energy date range:**  \n {start_date.date()} - {end_date.date()}")

# Ensure datetime index
if "time" in df_energy.columns:
    df_energy["time"] = pd.to_datetime(df_energy["time"]).dt.tz_localize(None)
    df_energy.set_index("time", inplace=True)
else:
    df_energy.index = pd.to_datetime(df_energy.index).tz_localize(None)

# Filter area
df_energy = df_energy[df_energy["pricearea"] == st.session_state.selected_area].copy()

# Ensure datetime index
if "time" in df_energy.columns:
    df_energy["time"] = pd.to_datetime(df_energy["time"]).dt.tz_localize(None)
    df_energy.set_index("time", inplace=True)
else:
    df_energy.index = pd.to_datetime(df_energy.index).tz_localize(None)

# Filter area
df_energy = df_energy[df_energy["pricearea"] == st.session_state.selected_area].copy()

# Filtered data
df_time_filtered = df_energy[(df_energy.index >= start_ts) & (df_energy.index <= end_ts)]
df_time_filtered = df_time_filtered.sort_values(by='time', ascending=True)

if df_time_filtered.empty:
    st.warning("No data found for the selected time window.")
    st.stop()

unique_groups_list = df_energy["groupname"].unique().tolist()

tab1, tab2 = st.tabs(["STL analysis", "Spectrogram"])
with tab1:
    st.subheader("Seasonal-Trend Decomposition using LOESS (STL)")
    col1, col2, col3 = st.columns([1, 1.5, 1.5])
    with col1:
        group_to_analyze_stl = st.selectbox("Type of data", options=unique_groups_list, key="group_to_analyze_stl")
    with col2:
        trend = st.slider("Trend Smoother", min_value=301, value=501, max_value=1000, step=2)
    with col3:
        seasonal = st.slider("Seasonal Smoother", min_value=7, value=13, max_value=31, step=2)

    from utils.stl_analyzer import analyze_decompose_STL

    daily = 24
    period = daily

    plot_decompose_elbub = analyze_decompose_STL(
        df_time_filtered,
        area=st.session_state["selected_area"],
        group=group_to_analyze_stl,
        period=period,
        seasonal_smoother=seasonal,
        trend_smoother=trend,
        robust=False,
    )

    st.plotly_chart(plot_decompose_elbub, use_container_width=True)

with tab2:
    st.subheader("Short-Time Fourier Transform (STFT) Spectrogram")
    col1, col2 = st.columns([1, 3])
    with col1:
        group_to_analyze_stft = st.selectbox("Type of data", options=unique_groups_list, key="group_to_analyze_stft")
    with col2:
        window_length = st.radio("Window length (hours)", [24, 168], horizontal=True)

    # ensure integer
    window_length = int(window_length)
    window_overlap = max(1, window_length // 4)

    from utils.spectrogram_analyzer import analyze_spectrogram_decomposition

    fig_spectrogram_decomposition = analyze_spectrogram_decomposition(
        df_time_filtered,
        area=st.session_state["selected_area"],
        group=group_to_analyze_stft,
        window_length=window_length,
        window_overlap=window_overlap,
        figsize=(12, 8),
    )

    st.plotly_chart(fig_spectrogram_decomposition)
