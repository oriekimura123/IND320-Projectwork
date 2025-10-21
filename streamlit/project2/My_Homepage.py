   # streamlit/Prosject2/My_Homepage.py
import sys
import os

# --- SOLUTION FOR IMPORTERRORS ---
# Navigates two levels up from /projects/project2/ to the Root Folder/
# and adds it to the search path
repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.append(repo_root)

# ----------------------------------

import streamlit as st
import pandas as pd

# Now this absolute import should work because 'core' is in sys.path
from core.data_loader import load_csv_with_pandas 

# --- Caching Function ---
@st.cache_data
def get_meteo_data():
    """
    Loads and caches the DataFrame. This function runs only once per app session 
    or when the underlying CSV file changes.
    """
    # Delegate the actual path handling and reading to the core module
    meteo_df = load_csv_with_pandas('open-meteo-subset.csv')
    
    # You can perform any final, one-time cleaning here if needed
    
    return meteo_df

# --- Load the Data Once ---
# Call the function early in the main app file. 
# The result (the DataFrame) is now stored in Streamlit's cache.
# We don't need to assign it to a global variable here, but the call pre-loads the data.
get_meteo_data() 

# --- Main App Content ---
st.set_page_config(page_title="My Projectwork", layout="wide")
st.title("Welcome to My Streamlit App for Projectwork-part2!")
st.write("This is the the front/home page.")
st.write("Orie Kimura")
st.write("Oct 24, 2025")