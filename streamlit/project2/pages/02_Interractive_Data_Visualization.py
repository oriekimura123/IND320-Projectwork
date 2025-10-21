# streamlit/Project2/pages/02_Interractive_Data_Visualization.py

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


st.title("Interactive Data Visualization")
st.write("A plot of the imported data (open-meteo-subset.csv), including header, axis titles and other relevant formatting.   \n"\
         "A drop-down menu (st.selectbox) choosing any single column in the CSV or all columns together.  \n "\
         "A selection slider (st.select_slider) to select a subset of the months. Defaults should be the first month.")

st.divider()

# Import the cached function from the main file
from My_Homepage import get_meteo_data
df = get_meteo_data()

# --- Selectbox  for column selection ---
# Get a list of column names except 'time'
all_columns_except_time = [col for col in df.columns if col != 'time']

# Get a list of the columns to plot, excluding the 'time' column. and add "All Columns" option
chart_columns = [col for col in df if col != 'time']
options_columns = ["All Columns"] + chart_columns

st.markdown('##### Select a data series to display:')

# Create the selectbox
selected_option = st.selectbox(
    " ",  # Use a space as the label to avoid showing the text twice
    options_columns,
    width=250
)

# Display the selected option
st.write(f"##### You selected: {selected_option}")

# --- Month Selection st.select_slider ---
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
month_to_num = {month: i + 1 for i, month in enumerate(months)}

# Find the minimum and maximum months present in the data for sensible defaults
min_month_num = df['time'].dt.month.min()
max_month_num = df['time'].dt.month.max()

min_month_name = [name for name, num in month_to_num.items() if num == min_month_num][0]
max_month_name = [name for name, num in month_to_num.items() if num == max_month_num][0]

st.divider()

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
display_months_data = df[(df['time'].dt.month >= start_month_num) & (df['time'].dt.month <= end_month_num)]


# --- Plotting Logic, Plotly ---
if display_months_data.empty:
    st.warning("No data available for the selected month range.")

elif selected_option == 'All Columns':
    # --- Plot Normalized Data ---
    st.markdown('#### Combined Plot: Normalized Data')

    # Create a copy
    df_normalized = display_months_data.copy()
    
    # Normalize the selected metric columns using a for loop
    for col in chart_columns:
        df_normalized[col] = min_max_normalize(df_normalized[col])

    # 1. Reshape the normalized filtered data from wide to long format for Plotly Express
    df_long = df_normalized.melt(
        id_vars='time', 
        value_vars=chart_columns, 
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
        y=selected_option,
        title=f"Trend for {selected_option} - {start_month_name} to {end_month_name}",
        labels={selected_option: selected_option, 'time': 'Date'}
    )
    st.markdown(f"Single Plot: {selected_option}")

# Add relevant formatting
fig.update_layout(
    xaxis_title="Date",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=60, b=20)
)

# Display the final plot
st.plotly_chart(fig, use_container_width=True)