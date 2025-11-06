# streamlit/Prosject3/03_Elhub_Data_Analysis.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft
from statsmodels.tsa.seasonal import STL
from typing import Tuple, Dict, Any

if 'plot_elhub_data' not in st.session_state:
    st.session_state['plot_elhub_data'] = pd.DataFrame()
    
if 'selected_area' not in st.session_state:
    st.session_state['selected_area'] = None

if 'selected_prod_group' not in st.session_state:
    # Default to None initially. The code below will set it to the first available metric column 
    st.session_state['selected_prod_group'] = None
    
# --- Tab Structure ---
st.title("Elhub production data Analysys")

tab1, tab2 = st.tabs(["STL analysis", "Spectrogram"])
with tab1:
    st.subheader("Seasonal-Trend Decomposition using LOESS (STL)")

    from utils.stl_analyzer import analyze_decompose_STL

    daily = 24
    period = daily

    plot_decompose_elbub = analyze_decompose_STL(
        st.session_state['plot_elhub_data'],
        area = st.session_state['selected_area'],
        prod_group = st.session_state['selected_prod_group'],
        period=period,
        robust=False)

    st.pyplot(plot_decompose_elbub)

with tab2:
    st.subheader("Short-Time Fourier Transform (STFT) Spectrogram")

    from utils.spectrogram_analyzer import analyze_spectrogram_decomposition
    
    fig_spectrogram_decomposition = analyze_spectrogram_decomposition(
        st.session_state['plot_elhub_data'],
        area = st.session_state['selected_area'],
        prod_group = st.session_state['selected_prod_group'],
        window_length  = 24*7,
        window_overlap = 12*7,
        figsize = (12, 8)) 

    st.pyplot(fig_spectrogram_decomposition)

