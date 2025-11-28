# streamlit/Prosject4/08_Predictive_Forecasting.py

import streamlit as st
import pandas as pd
from datetime import date
from utils.utils import initialize_session_state, draw_analysis_context_sidebar
from utils.data_loaders import load_mongoDB, load_all_era5_data
from utils.sarimax import run_SARIMAX_model

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

def adjust_end_train_date(end_train: pd.Timestamp, freq: str) -> pd.Timestamp:
    """Align end_train to valid resample period boundaries."""
    
    if freq == "Daily":
        return end_train  # any day is valid

    if freq == "Weekly":
        # pandas weekly (W) ends on Sunday
        # If the selected date is not Sunday, go back to previous Sunday
        weekday = end_train.weekday()  # Monday=0, Sunday=6
        offset = (weekday - 6) % 7
        return end_train - pd.Timedelta(days=offset)

    if freq == "Monthly":
        # end of training must be the last completed month
        # If user picks inside a month → go to last day of previous month
        first_of_month = end_train.replace(day=1)
        last_prev_month = first_of_month - pd.Timedelta(days=1)
        return last_prev_month

    return end_train

# Load data (assume these functions are cached)
df_weather = load_all_era5_data(COORDS_DF)
df_prod = load_mongoDB(MONGO_COLLECTION_PRODUCTION, MONGO_DATABASE)
df_cons = load_mongoDB(MONGO_COLLECTION_CONSUMPTION, MONGO_DATABASE)

# Short-circuit if selection not locked
if not st.session_state.filtering_confirmed:
    st.error("Please configure the Area and type of data on the Home page first.")
    st.stop()

st.subheader(f"SARIMAX Model for energy data — area {st.session_state.selected_area}")

date_range = st.slider("Select data period", min_value=MIN_DATE, max_value=MAX_DATE, value=[MIN_DATE, MAX_DATE], format="YYYY-MM-DD", key="sarimax_date_range")
start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
end_date = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# draw_analysis_context
st.sidebar.header("Current Selection")
area = st.session_state.get("selected_area", "N/A")
data_type = st.session_state.get("selected_energy_datatype", "N/A")
st.sidebar.info(f"**{area}**")

# ensure datetime index
if "time" in df_weather.columns:
    df_weather["time"] = pd.to_weather(df_prod["time"]).dt.tz_localize(None)
    df_weather.set_index("time", inplace=True)
else:
    df_prod.index = pd.to_datetime(df_prod.index).tz_localize(None)

if "time" in df_prod.columns:
    df_prod["time"] = pd.to_datetime(df_prod["time"]).dt.tz_localize(None)
    df_prod.set_index("time", inplace=True)
else:
    df_prod.index = pd.to_datetime(df_prod.index).tz_localize(None)

if "time" in df_cons.columns:
    df_cons["time"] = pd.to_datetime(df_cons["time"]).dt.tz_localize(None)
    df_cons.set_index("time", inplace=True)
else:
    df_cons.index = pd.to_datetime(df_cons.index).tz_localize(None)

# Filter area
df_weather = df_weather[df_weather["pricearea"] == st.session_state.selected_area].copy()
df_prod = df_prod[df_prod["pricearea"] == st.session_state.selected_area].copy()
df_cons = df_cons[df_cons["pricearea"] == st.session_state.selected_area].copy()

# pivot
prod_wide = df_prod.pivot_table(index="time", columns=["datatype", "groupname"], values="quantitykwh")
cons_wide = df_cons.pivot_table(index="time", columns=["datatype", "groupname"], values="quantitykwh")
df_all = pd.concat([prod_wide, cons_wide, df_weather], axis=1, join='outer')

# normalize index
if not isinstance(df_all.index, pd.DatetimeIndex):
    df_all.index = pd.to_datetime(df_all.index).tz_localize(None)
else:
    if df_all.index.tz is not None:
        df_all.index = df_all.index.tz_convert(None)

# flatten multiindex columns to strings for simpler selection & SARIMAX
if isinstance(df_all.columns, pd.MultiIndex):
    df_all.columns = ["_".join(map(str, c)) for c in df_all.columns if c != 'pricearea']

df_all = df_all.sort_index()
df_filtered = df_all.loc[start_date:end_date].copy()

# Use interpolate to fill short gaps, then fill any remaining NaNs with 0 
df_filtered = df_filtered.interpolate(method='linear', limit=24).fillna(0) 
df_filtered.index.freq = 'h'

# model parameters
st.markdown("##### Model Parameter Selection")
col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1, 1, 1.2])

available_targets = [col for col in df_all.columns if col != 'pricearea']

with col1:
    target_col = st.selectbox("Target Variable (Y)", options=available_targets, index=0)
    # pick columns corresponding to the chosen group
    possible_exog = [c for c in df_all.columns if c != target_col and c != 'pricearea']

with col2:
    selected_exog = st.multiselect("Exogenous Variables (optional)", options=possible_exog, default=[])

with col3:
    end_train_date = st.date_input("End of Training Date", value=date_range[0] + (date_range[1] - date_range[0]) / 2, min_value=date_range[0], max_value=date_range[1])
    end_train = pd.to_datetime(end_train_date)

with col4:
    freq_option = st.selectbox(
        "Aggregation Frequency",
        ["Hourly", "Daily", "Weekly", "Monthly"],
        index=0
    )
    end_train_adj = adjust_end_train_date(end_train, freq_option)

with col5:
    run_model = st.button("Run SARIMAX Model")
    st.caption("Click to train and generate forecast.")

if run_model:
    if df_filtered.empty or len(df_filtered) < 50:
        st.error("Not enough data to estimate SARIMAX model.")
    else:
        with st.spinner("Fitting SARIMAX model…"):
            fig, captured_warnings = run_SARIMAX_model(
                df=df_filtered,
                plott_start_date=date_range[0],
                end_train=end_train_adj,
                target=target_col,
                exog_vars=selected_exog,
                freq=freq_option
            )
        # Display the warnings first
        if captured_warnings:
            st.warning("⚠️ Model Warnings Encountered:")
            unique_warnings = set(captured_warnings)

            for w in unique_warnings:
                st.markdown(f"- {w}")

        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Select parameters, then click **Run SARIMAX Model**.")