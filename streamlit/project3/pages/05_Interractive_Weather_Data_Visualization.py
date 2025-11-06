# streamlit/Project2/pages/05_Interractive_Weather_Data_Visualization.py

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

# --- Function for Normalization ---
def min_max_normalize(series):
    """Applies Min-Max scaling to a pandas Series, resulting in values between 0 and 1."""
    min_val = series.min()
    max_val = series.max()
    # Handle case where min_val equals max_val to avoid division by zero
    if max_val == min_val:
        return series - min_val
    return (series - min_val) / (max_val - min_val)

city_data = {
    "pricearea": ["NO1", "NO2", "NO3", "NO4", "NO5"],
    "city_names": ["Oslo", "Kristiansand", "Trondheim", "Tromsø", "Bergen"],
    "lon": [10.7461, 7.9956, 10.3951, 18.957, 5.328],
    "lat": [59.9127, 58.1467, 63.4305, 69.6496, 60.392],
}

COORDS_DF = pd.DataFrame(city_data)
## Set the 'pricearea' as the index for efficient lookup
COORDS_DF = COORDS_DF.set_index('pricearea')

# Initialize session state variables if they don't exist
if 'selected_area' not in st.session_state:
    st.session_state['selected_area'] = COORDS_DF.index[0] # Default to the first area in the list

selected_year = "2021"
selected_month_num = 1
selected_month_name = 'January'

from utils.data_loaders import load_era5_data_for_area
load_era5_data_for_area(st.session_state['selected_area'], selected_year)


# Use a single DataFrame key
if 'era5_data_raw' not in st.session_state:
    st.session_state['era5_data_raw'] = pd.DataFrame()

st.title("Interactive Weather Data Visualization")

st.write(f"Weather Data : {selected_year}, area : {st.session_state['selected_area']}")

st.write("A plot of the weather data from https://archive-api.open-meteo.com/v1/era5,  \n"\
         "including header, axis titles and other relevant formatting.   \n"\
         "A drop-down menu (st.selectbox) choosing any single column or all columns together.  \n "\
         "A selection slider (st.select_slider) to select a subset of the months. Defaults should be the first month.")
st.write("Updated, Nov 07, 2025")

# Import the file
# from utils.data_loaders import get_meteo_csv
# METEO_FILEPATH = "open-meteo-subset.csv" 

# Load the data using the cached function
#df_meteo = get_meteo_csv(METEO_FILEPATH)

raw_df = st.session_state['era5_data_raw']
raw_df = raw_df.reset_index()
# df_with_time_column = raw_df.reset_index()

raw_df['time'] = pd.to_datetime(raw_df['time'], errors='coerce')

# --- Selectbox  for column selection ---
# Get a list of the columns to plot, excluding the 'time' column. and add "All Columns" option
options_columns = [col for col in raw_df if col != 'time']
# options_columns = ["All Columns"] + chart_columns

st.markdown('##### Select a data series to display:')

if 'selected_column' not in st.session_state:
    # Default to None initially. The code below will set it to the first available metric column 
    st.session_state['selected_column'] = None

# Create the selectbox
selected_column = st.selectbox(
    " ",  # Use a space as the label to avoid showing the text twice
    options_columns,
    width=250
#    index=options_columns.index(st.session_state['selected_column'])
)

# selected_column = st.selectbox(
#    "Metric to Display (Line Plot)",
#    options_columns,
#    width=250,
#    key='metric_selector',
#    label_visibility='collapsed',
#    # Ensure the UI reflects the current state (which is guaranteed to be one of the options)
#    index=options_columns.index(st.session_state['selected_column']) 
#)
# Store the result in session state (key handles this, but explicitly set for robustness)
st.session_state['selected_column'] = selected_column

# st.write(f"##### Displayed Metric: {st.session_state['selected_column']}")


# Display the selected column
st.write(f"##### You selected: {selected_column}")

# --- Month Selection st.select_slider ---
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
month_to_num = {month: i + 1 for i, month in enumerate(months)}

# Find the minimum and maximum months present in the data for sensible defaults
min_month_num = raw_df['time'].dt.month.min()
max_month_num = raw_df['time'].dt.month.max()

min_month_name = [name for name, num in month_to_num.items() if num == min_month_num][0]
max_month_name = [name for name, num in month_to_num.items() if num == max_month_num][0]

st.markdown('##### Select a range of months:')

# Use st.select_slider to get the start and end month names
start_month_name, end_month_name = st.select_slider(
    " ",
    options=months[min_month_num-1 : max_month_num], # Only show months present in the data
    value=(min_month_name, max_month_name) # Default to the full range of data
)

# --- Filtering data to display ---
start_month_num = month_to_num[start_month_name]
end_month_num = month_to_num[end_month_name]

# Filter the DataFrame based on month number
display_months_data = raw_df[(raw_df['time'].dt.month >= start_month_num) & (raw_df['time'].dt.month <= end_month_num)]

# --- Plotting Logic, Plotly ---
if display_months_data.empty:
    st.warning("No data available for the selected month range.")

elif selected_column == 'All Columns':
    # --- Plot Normalized Data ---
    st.markdown('#### Combined Plot: Normalized Data')

    # Create a copy
    df_normalized = display_months_data.copy()
    
    # Normalize the selected metric columns using a for loop
    for col in options_columns:
        df_normalized[col] = min_max_normalize(df_normalized[col])

    # Reshape the normalized filtered data from wide to long format for Plotly Express
    df_long = df_normalized.melt(
        id_vars='time', 
        value_vars=options_columns, 
        var_name='Metric', 
        value_name='Normalized Value'
    )

    fig = px.line(
        df_long,
        x='time',
        y='Normalized Value',
        color='Metric',
        title=f"All Metrics (Normalized) - {start_month_name} to {end_month_name}",
        labels={'Normalized Value': 'Normalized Value (0 to 1)', 'time': 'Date'}
    )
    st.caption("All metrics have been scaled (0 to 1) to allow comparison of relative trends.")

else:
    # --- Plot single selected column (Raw Data) ---
    fig = px.line(
        display_months_data,
        x='time',
        y=selected_column,
        title=f"Trend for {selected_column} - {start_month_name} to {end_month_name}",
        labels={selected_column: selected_column, 'time': 'Date'}
    )

# Add relevant formatting
fig.update_layout(
    xaxis_title="Date",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=60, b=20)
)

# Display the final plot
st.plotly_chart(fig, use_container_width=True)
st.session_state['df_display_data'] = display_months_data