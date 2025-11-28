# streamlit/Prosject4/02_Visualization_Energy_data.py

import streamlit as st
import pandas as pd
import plotly.express as px
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

# Select which df to use
if st.session_state.selected_energy_datatype == "Production data":
    df_energy = df_prod.copy()
else:
    df_energy = df_cons.copy()

# Ensure datetime index
if "time" in df_energy.columns:
    df_energy["time"] = pd.to_datetime(df_energy["time"]).dt.tz_localize(None)
    df_energy.set_index("time", inplace=True)
else:
    df_energy.index = pd.to_datetime(df_energy.index).tz_localize(None)

# Filter area
df_energy = df_energy[df_energy["pricearea"] == st.session_state.selected_area].copy()

# Date range UI
st.subheader(f"Visualization of Energy data in area {st.session_state.selected_area}")
current_range = st.session_state.date_range_1_2

# Select data period
new_dates = st.slider("Select data period", min_value=MIN_DATE, max_value=MAX_DATE, value=current_range, format="YYYY-MM-DD", key="viz_date_range")
if len(new_dates) == 2 and new_dates != current_range:
    st.session_state.date_range_1_2 = new_dates

start_date, end_date = st.session_state.date_range_1_2
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# draw_analysis_context
st.sidebar.header("Current Selection")
area = st.session_state.get("selected_area", "N/A")
data_type = st.session_state.get("selected_energy_datatype", "N/A")
st.sidebar.info(f"**{area}, {data_type}**")

# Sidebar context
st.sidebar.info(f"**Energy data period:**  \n {start_date} - {end_date}")

# Filtered data
df_time_filtered = df_energy[(df_energy.index >= start_ts) & (df_energy.index <= end_ts)]
df_time_filtered = df_time_filtered.sort_values(by='time', ascending=True)
df_time_filtered = df_time_filtered.reset_index()

if df_time_filtered.empty:
    st.warning("No data found for the selected time window.")
    st.stop()

# Colormap
colormap_production = {
    "hydro": "#1f77b4",
    "wind": "#17becf",
    "thermal": "#7f7f7f",
    "solar": "#e377c2",
    "other": "#2ca02c",
}

colormap_consumption = {
    "cabin": "#1f77b4",
    "primary": "#17becf",
    "secondary": "#7f7f7f",
    "primary": "#e377c2",
    "household": "#2ca02c",
}

# Plotting
col1, col2 = st.columns([1, 2])
with col1:
    if st.session_state.selected_energy_datatype == "Production data":
        title_text = f"Production Distribution in {st.session_state.selected_area}"
        COLOR_MAP = colormap_production
    else:
        title_text = f"Consumption Distribution in {st.session_state.selected_area}"
        COLOR_MAP = colormap_consumption

    df_pie = df_time_filtered.groupby("groupname")["quantitykwh"].sum().reset_index()
    if not df_pie.empty and df_pie["quantitykwh"].sum() > 0:
        total_kwh = df_pie["quantitykwh"].sum()
        fig_pie = px.pie(df_pie, names="groupname", values="quantitykwh", color_discrete_map=COLOR_MAP, title=f"{title_text} <br> (Total kwh: {total_kwh:,.0f})")
        fig_pie.update_traces(textinfo="percent+label", rotation=180, marker=dict(line=dict(color="#000000", width=1)))
        st.plotly_chart(fig_pie)
    else:
        st.warning(f"No {st.session_state.selected_energy_datatype} data found for {st.session_state.selected_area}.")

with col2:
    if st.session_state.selected_energy_datatype == "Production data":
        title_text = f"Production trend in {st.session_state.selected_area}, {start_date} - {end_date}"
    else:
        title_text = f"Consumption trend in {st.session_state.selected_area}, {start_date} - {end_date}"

    df_plot_pd = df_time_filtered.groupby(["time", "groupname"], as_index=False)["quantitykwh"].sum()
    if not df_plot_pd.empty:
        fig_line = px.line(df_plot_pd, x="time", y="quantitykwh", color="groupname", color_discrete_map=COLOR_MAP, title=title_text, labels={"quantitykwh": "Production (kWh)", "time": "Date"})
        fig_line.update_xaxes(tickformat="%d %b %Y")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning(f"No {st.session_state.selected_energy_datatype} data found for {st.session_state.selected_area}.")