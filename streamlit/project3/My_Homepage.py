   # streamlit/Prosject2/My_Homepage.py
import sys
import os
import streamlit as st
from pathlib import Path

import os, sys

# Adds the Root Folder to the search path BEFORE importing from 'utils'

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Main App Content ---
st.set_page_config(page_title="My Projectwork", layout="wide")
st.title("Welcome to My Streamlit App for Projectwork-part3!")
st.write("This is the the front/home page.")
st.write("Orie Kimura")
st.write("Nov 7, 2025")

st.write("This app contains the following pages:")

markdown_list = """
    - Elhub Production Data:  
    The app loads Elhub production data for 2021, downloaded from https://api.elhub.no/energy-data/v0/price-areas.   
    Users can select a price area and a production type for further analysis. The initial data is displayed using a pie chart and a line chart.

    - Elhub Data Analysis:  
    Analysis includes Seasonal-Trend Decomposition using LOESS (STL) and Short-Time Fourier Transform (STFT) Spectrogram.   
    These methods are performed on the selected Elhub production data for 2021 (price area and production type) and the results are displayed.

    - Weather Data Visualization:  
    Weather data for the selected Elhub price area is loaded from https://archive-api.open-meteo.com/v1/era5 for 2021 and displayed.  
    The cities used to represent each price area in the analysis are: NO1: Oslo, NO2: Kristiansand, NO3: Trondheim, NO4: Tromsø, and NO5: Bergen.

    - Interactive Weather Data Visualization:  
    The weather data for the selected price area (using the representative city) in 2021 is displayed.   
    Users can select a specific weather feature and a range of months for more focused analysis.

    - Weather Data Analysis:  
    Outlier/SPC analysis and Anomaly/LOF analysis are performed on the weather data,   
    utilizing the selected weather feature and month range for 2021, and the results are displayed.
"""
st.markdown(markdown_list)