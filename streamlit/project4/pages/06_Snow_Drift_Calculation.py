# streamlit/Prosject4/06_Snow_Drift_Calculation.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
from utils.utils import initialize_session_state
from utils.data_loaders import load_all_era5_data
from utils.snow_drift import compute_average_sector, compute_fence_height, plot_rose2, compute_yearly_results

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

# ensure datetime index
if "time" in df_weather.columns:
    df_weather["time"] = pd.to_datetime(df_weather["time"]).dt.tz_localize(None)
    df_weather.set_index("time", inplace=True)
else:
    df_weather.index = pd.to_datetime(df_weather.index).tz_localize(None)

# Filter area
df_weather = df_weather[df_weather["pricearea"] == st.session_state.selected_area].copy()

# Page start
st.subheader(f"Snow Drift Calculation and plotting {st.session_state.selected_area}")
st.markdown(f"Coordinates: **Lat {st.session_state.last_pin[0]:.2f}, Lon {st.session_state.last_pin[1]:.2f}**")

# draw_analysis_context
st.sidebar.header("Current Selection")
area = st.session_state.get("selected_area", "N/A")
data_type = st.session_state.get("selected_energy_datatype", "N/A")
st.sidebar.info(f"**{area}**")

# calculate season
df_weather["season"] = df_weather.index.to_series().apply(lambda dt: dt.year if dt.month >= 7 else dt.year - 1)

# Date range UI
unique_start_years = sorted(df_weather["season"].unique().tolist())
if len(unique_start_years) < 1:
    st.warning("Insufficient data to compute seasons.")
    st.stop()

season_options = [f"{y}-{y+1}" for y in unique_start_years]
selected_seasons_str = st.multiselect("Choose one or more seasons to include in the analysis:", options=season_options, default=season_options)
if not selected_seasons_str:
    st.warning("Please select at least one season to proceed.")
    st.stop()

selected_start_years = [int(s.split("-")[0]) for s in selected_seasons_str]
df_analysis = df_weather[df_weather["season"].isin(selected_start_years)].copy()

min_year = min(selected_start_years)
max_year = max(selected_start_years) + 1
actual_start_date = datetime(min_year, 7, 1).date()
actual_end_date = datetime(max_year, 6, 30).date()

# Parameters
T = 3000
F = 30000
theta = 0.5

yearly_df = compute_yearly_results(df_analysis, T, F, theta)
if yearly_df.empty:
    st.warning("No yearly results computed.")
    st.stop()

overall_avg_kgm = yearly_df["Qt (kg/m)"].mean()
overall_avg_tonnes = overall_avg_kgm / 1000

col1, col2 = st.columns(2)
# col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Overall Average Annual Snow Transport ($Q_t$)", value=f"{overall_avg_tonnes:,.1f} tonnes/m", help="Mean Q_t over selected seasons.")
# with col2:
    st.markdown("##### Tabler (2003) Model Parameters")
    st.code(f"Max Transport (T): {T} m\nFetch (F): {F} m\nRelocation Coeff (θ): {theta}")

yearly_df_disp = yearly_df.copy()
yearly_df_disp["$Q_t$ (tonnes/m)"] = yearly_df_disp["Qt (kg/m)"] / 1000

# with col3:
#     st.markdown("##### Annual Snow Transport and Controlling Factor")
#     st.dataframe(yearly_df_disp[["season", "$Q_t$ (tonnes/m)", "Control"]], hide_index=True)

# col1, col2 = st.columns(2)
# with col1:
    # fig_yearly = go.Figure()
    # fig_yearly.add_trace(go.Bar(x=yearly_df_disp["season"], y=yearly_df_disp["$Q_t$ (tonnes/m)"], marker_color="royalblue", name="Annual Snow Transport"))
    # fig_yearly.update_layout(title="Calculated Annual Snow Transport ($Q_t$) per Season", xaxis_title="Season", yaxis_title="$Q_t$ (tonnes/m)", height=400)
    # st.plotly_chart(fig_yearly, use_container_width=True)

with col2:
    st.markdown("##### Snow Fence Height Requirements")
    fence_types = ["Wyoming", "Slat-and-wire", "Solid"]
    fence_results = []
    for idx, row in yearly_df.iterrows():
        season = row["season"]
        Qt_val = row["Qt (kg/m)"]
        res = {"Season": season}
        for ft in fence_types:
            res[f"{ft} (m)"] = compute_fence_height(Qt_val, ft)
        fence_results.append(res)
    fence_df = pd.DataFrame(fence_results)
    st.dataframe(fence_df, hide_index=True)

st.markdown("##### Average Directional Snow Transport (Wind Rose)")
avg_sectors = compute_average_sector(df_analysis)
rose2 = plot_rose2(avg_sectors, overall_avg_kgm)
st.plotly_chart(rose2, use_container_width=True)



