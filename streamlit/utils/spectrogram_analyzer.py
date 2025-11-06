# streamlit_app/utils/spc_analyzer.py
# Function to perform spectrogram_decomposition and returen figure

import numpy as np
import matplotlib.pyplot as plt
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
) -> plt.Figure:
    """
    Args:
        df (pd.DataFrame): data DataFrame.
        area (str): The price area (e.g., 'NO3').
        prod_group (str): The production group (e.g., 'hydro').
        window_length (int): The STFT window length (nperseg). Defaults to 168 (weekly).
        figsize (Tuple[float, float]): Size of the output figure.
        
    Returns:
        plt.Figure: The Matplotlib Figure object.
    """
    
    # Apply the filter
    df_filtered = df.copy()

    # Basic check to prevent crash if data is empty
    if df_filtered.empty:
        # print(f"Error: No data found for Area: {area} and Group: {prod_group}. Cannot perform STFT.")
        st.write(f"Error: No data found for Area: {area} and Group: {prod_group}. Cannot perform STFT.")
        return plt.figure()
        
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
    
    # --- Map STFT times back to actual datetimes (using the time vector t) ---
    # The time vector 't' is measured in hours (samples) since fs=1.0
    start_time = df_filtered.index[0]
    datetime_labels = [start_time + pd.to_timedelta(i, unit='h') for i in t]
    
    # --- Plotting ---
    fig, axs = plt.subplots(2, 1, figsize=figsize, sharex=True)

    # Top Plot (Time Series)
    axs[0].plot(df_filtered.index, df_filtered['quantitykwh'], label='Production', color='tab:blue')
    axs[0].set_ylabel('Amplitude (QuantityKwh)')
    axs[0].set_title(f'Time Series and Spectrogram for {prod_group} in {area} (Window={window_length}h, Overlap={window_overlap}h )')
    axs[0].grid(True, linestyle='--', alpha=0.6)

    # Bottom Plot (Spectrogram)
    pcm = axs[1].pcolormesh(
        # df['date'],
        datetime_labels, 
        f, 
        np.abs(Zxx),
        shading='nearest', 
        vmin=0,
        vmax=np.max(np.abs(Zxx)) / 2
    )
    fig.colorbar(pcm, ax=axs[1], label='Amplitude')

    axs[1].set_ylabel('Frequency [cycles/hour]')
    axs[1].set_xlabel('Date')
    axs[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()

    # Rotate X-labels for better readability
    for ax in axs:
        ax.tick_params(axis='x', rotation=45) 
        
    plt.tight_layout()
    return fig