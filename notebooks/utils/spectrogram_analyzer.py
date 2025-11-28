# streamlit_app/utils/spc_analyzer.py
# Function to perform spectrogram_decomposition and returen figure

import numpy as np
# import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from scipy.signal import stft
from typing import Tuple
import matplotlib.dates as mdates
import streamlit as st

def analyze_spectrogram_decomposition(
    df: pd.DataFrame,
    area: str,
    prod_group: str,
    window_length: int = 168,
    window_overlap: int = 84,
    figsize: Tuple[float, float] = (10, 6)
#) -> Tuple[plt.Figure, pd.DataFrame]:
) -> go.Figure:
    """
    Args:
        df (pd.DataFrame): data DataFrame.
        area (str): The price area (e.g., 'NO3').
        prod_group (str): The production group (e.g., 'hydro').
        window_length (int): The STFT window length (nperseg). Defaults to 168 (weekly).
        figsize (Tuple[float, float]): Size of the output figure.
        
    Returns:
        go.Figure: The plotly Figure object.
    """
    
    # Apply the filter
    df_filtered = df.copy()

    # Basic check to prevent crash if data is empty
    if df_filtered.empty:
        # print(f"Error: No data found for Area: {area} and Group: {prod_group}. Cannot perform STFT.")
        st.write(f"Error: No data found for Area: {area} and Group: {prod_group}. Cannot perform STFT.")
        return go.Figure()
        
    # --- Perform STFT ---
    # df_filtered.index = pd.to_datetime(df_filtered.index)
    df_filtered['starttime'] = pd.to_datetime(df_filtered['starttime'])
    df_filtered = df_filtered.set_index('starttime')
    f, t, Zxx = stft(
        df_filtered['quantitykwh'], 
        fs = 1.0, # Data is hourly (1 sample per hour)
        nperseg = window_length, 
        noverlap = window_overlap
    )
    
    power_spectrum = np.abs(Zxx)**2 

    # Add a small epsilon before log to prevent log(0) errors.
    log_power_spectrum = np.log10(power_spectrum + 1e-10)

    # --- Map STFT times back to actual datetimes (using the time vector t) ---
    # The time vector 't' is measured in hours (samples) since fs=1.0
    start_time = df_filtered.index[0]
    datetime_labels = [start_time + pd.to_timedelta(i, unit='h') for i in t]
    
    # Create a figure with two stacked rows (for Time Series and Spectrogram)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        # Ratio of heights: Time Series (1 part), Spectrogram (3 parts)
        row_heights=[0.25, 0.75], 
        subplot_titles=[
            f'{prod_group.capitalize()} time series in area {area}',
            'STFT Spectrogram (Log Power)'
        ]
    )

    # --- ROW 1: Time Series Plot (Line Plot) ---
    fig.add_trace(
        go.Scatter(
            x=df_filtered.index,
            y=df_filtered['quantitykwh'].values,
            mode='lines',
            line=dict(color='blue')
        ),
        row=1, col=1
    )

    # --- ROW 2: Spectrogram Plot (Heatmap) ---
    fig.add_trace(
        go.Heatmap(
            z=log_power_spectrum,
            x=datetime_labels, 
            y=f,
            colorscale='Viridis',
            colorbar=dict(title='Log Power')
        ),
        row=2, col=1
    )

    fig.update_layout(
        height=800
    )

    return fig