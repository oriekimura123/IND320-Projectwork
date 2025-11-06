# streamlit/Project2/pages/04_Weather_Data_Visualiization.py
# Import the cached function from the main file
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

# Define the file path
# METEO_FILEPATH = "open-meteo-subset.csv" 

# Load the data using the cached function
# df_meteo = get_meteo_csv(METEO_FILEPATH)
# df_meteo['time'] = pd.to_datetime(df_meteo['time'], errors='coerce')

city_data = {
    "pricearea": ["NO1", "NO2", "NO3", "NO4", "NO5"],
    "city_names": ["Oslo", "Kristiansand", "Trondheim", "Tromsø", "Bergen"],
    "lon": [10.7461, 7.9956, 10.3951, 18.957, 5.328],
    "lat": [59.9127, 58.1467, 63.4305, 69.6496, 60.392],
}

COORDS_DF = pd.DataFrame(city_data)
## Set the 'pricearea' as the index for efficient lookup
COORDS_DF = COORDS_DF.set_index('pricearea')

st.title("Data Visualization - Weather data January 2021")
st.write("A table showing the imported data from https://archive-api.open-meteo.com/v1/era5.   \n "\
         "Use the row-wise LineChartColumn() to display the first month of the data series.  \n "\
         "There should be one row in the table for each column of the imported data.")
st.write("Updated, Nov 07, 2025")

selected_year = "2021"
selected_month_num = 1
selected_month_name = 'January'

# Initialize session state variables if they don't exist
if 'selected_area' not in st.session_state:
    st.session_state['selected_area'] = COORDS_DF.index[0] # Default to the first area in the list

from utils.data_loaders import load_era5_data_for_area
load_era5_data_for_area(st.session_state['selected_area'], selected_year)

# Use a single DataFrame key
if 'era5_data_raw' not in st.session_state:
    st.session_state['era5_data_raw'] = pd.DataFrame()

raw_df = st.session_state['era5_data_raw']

if not raw_df.empty:
    
    # --- Filter for the Selected Month ---
    
    df = raw_df.copy()

    # Temporarily remove timezone for accurate month comparison
    if df.index.tz is not None:
         naive_index = df.index.tz_localize(None)
    else:
         naive_index = df.index

    # Filter for the selected month number (now dynamic)
    filtered_month_df = df[naive_index.month == selected_month_num]
    
    if not filtered_month_df.empty:
        st.subheader(f"Raw {selected_month_name} data in {selected_year} for {st.session_state['selected_area']} (First 5 Rows)")
        st.dataframe(filtered_month_df.head())
        
        st.markdown("---")
        
        st.write(f"Displaying **{len(filtered_month_df):,}** hourly data points for {selected_month_name} in {selected_year} for {st.session_state['selected_area']} .")
        
        # Reset index to make 'time' a column for plotting
        filtered_month_df = filtered_month_df.reset_index()
        
        # Get a list of the columns to plot, excluding the 'time' column.
        chart_columns = [col for col in filtered_month_df.columns if col != 'time']

        # Create a new DataFrame to hold the reshaped data for the charts.
        st.subheader(f"Weather Data : Line Charts {selected_month_name} in {selected_year} for {st.session_state['selected_area']}")
        df_charts = pd.DataFrame({
            'Metric': chart_columns,
            'Trend over Time': [filtered_month_df[col].tolist() for col in chart_columns]
        })

        # Display the transformed DataFrame with embedded line charts.
        st.dataframe(
            df_charts,
            column_config={
                "Trend over Time": st.column_config.LineChartColumn(
                    "Trend over Time for January",
                    width=1000
                )
            },
            hide_index=True,
        )        
        
    else:
         st.warning(f"{selected_month_name} data filtered successfully, but the resulting DataFrame is empty (Data may not cover full year range).")
else:
    st.warning("No data available to display. Please select an area and year, then click 'Load Data'.")

st.write("###### Note: The line charts above are small multiples, each representing the trend of a specific weather metric over the days of January. This format allows for easy comparison across different metrics.")