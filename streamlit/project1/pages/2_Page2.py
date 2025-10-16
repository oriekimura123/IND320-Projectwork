# Projectwork-part1/pages/2_Page2.py
import streamlit as st
import pandas as pd

# Import the cached function from the main file
from Projectwork_part1 import get_meteo_data
df = get_meteo_data()


st.title("Page 2")
st.write("### Data Visualization of open-meteo-subset.csv")
st.write("###### A table showing the imported data. " \

"Use the row-wise LineChartColumn() to display the first month of the data series. " \
"There should be one row in the table for each column of the imported data.")


# Create a subset of the DataFrame for January and display it
january_data = df[df['time'].dt.month == 1]
st.subheader("Weather Data : Table header for January")
st.dataframe(january_data.head())

# Get a list of the columns to plot, excluding the 'time' column.
chart_columns = [col for col in january_data.columns if col != 'time']

# Create a new DataFrame to hold the reshaped data for the charts.
st.subheader("Weather Data : Line Charts for January")
df_charts = pd.DataFrame({
    'Metric': chart_columns,
    'Trend over Time': [january_data[col].tolist() for col in chart_columns]
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

st.write("###### Note: The line charts above are small multiples, each representing the trend of a specific weather metric over the days of January. This format allows for easy comparison across different metrics.")