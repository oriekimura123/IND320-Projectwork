   # Projectwork-part1.py
import sys
import os
import streamlit as st
import pandas as pd



# Finds the path to your Streamlit app folder: projects/project1
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigates two levels up to the Root Folder (from projects/project1/ to the Root)
repo_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

# Adds the Root Folder to the search path BEFORE importing from 'core'
if repo_root not in sys.path:
    sys.path.append(repo_root)

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
get_meteo_data() 

# --- Main App Content ---
st.set_page_config(page_title="My Projectwork", layout="wide")
st.title("Welcome to My Streamlit App for Projectwork-part1!")
st.write("This is the the front/home page.")
st.write("Orie Kimura")
st.write("~~Oct 3, 2025~~")
st.write("Oct 16, 2025")