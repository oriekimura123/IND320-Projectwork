import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime
import os 
from typing import Optional, Dict, Any

@st.cache_data(show_spinner=True)
def lagged_correlation_plot(x, y, lag=7, window=45, center_idx=22, variable='feature'):
    """
    Generates a Plotly figure showing lagged correlation and focused time series.
    
    Args:
        x (pd.DataFrame): The independent (Weather) DataFrame containing 'variable'.
        y (pd.Series): The dependent (Energy) series (Target).
        lag (int): The lag in time steps (days) to apply to x.
        window (int): The size of the rolling window for correlation calculation.
        center_idx (int): The index of the point used to center the focus window.
        variable (str): The column name in x to correlate against y.
    """
    
    # 1. Calculate Correlation
    
    # Create the lagged series Z from X
    z = x[variable].copy()
    
    # Apply lag to the index. Assuming 'x' has a datetime index.
    try:
        # Shift X (Weather) by the lag amount
        z.index = z.index.shift(lag, freq=z.index.freq)
    except Exception as e:
        st.error(f"Error shifting index for lag: {e}. Ensure data has a consistent time frequency.")
        return go.Figure()


    # Overall Correlation (using only overlapping data points)
    overlap_index = y.index.intersection(z.index)
    
    if overlap_index.empty:
        # This can happen if the lag pushes all dates out of the analysis window
        st.warning("No overlapping dates for correlation after applying lag. Try reducing the lag.")
        return go.Figure()
        
    y_overlap = y.loc[overlap_index]
    z_overlap = z.loc[overlap_index]
    
    # Calculate simple Pearson correlation for the title
    corr_value = y_overlap.corr(z_overlap)
    
    # Sliding Window Correlation (SWC)
    SWC = y.rolling(window, center=True).corr(z)

    # 2. Plotting Parameters
    x_full = y.index
    y_len = len(y)
    
    # Calculate the boundaries for the focus window based on the center_idx
    half_window = window // 2
    
    start_idx_focus = np.max([0, center_idx - half_window])
    end_idx_focus = np.min([y_len, center_idx + half_window])
    
    # Convert index boundaries to actual datetime objects for Plotly highlighting
    start_date_focus = x_full[start_idx_focus]
    end_date_focus = x_full[end_idx_focus]

    # 3. Create Subplots
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=[
            y.name, 
            variable, 
            f'Sliding Window Correlation ({window}-day window)'
        ]
    )
    
    # --- ROW 1: Time Series Plot Y (Energy Sub-Type) ---
    fig.add_trace(
        go.Scatter(
            x = x_full,
            y = y,
            mode='lines',
            name=f'{y.name} Full',
            line=dict(color='blue', width=0.5),
            showlegend=False
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x = x_full[start_idx_focus:end_idx_focus],
            y = y.iloc[start_idx_focus:end_idx_focus],
            mode='lines',
            name=f'{y.name} Focus',
            line=dict(color='red', width=1),
            showlegend=False
        ), 
        row=1, col=1
    )
    
    fig.update_yaxes(title_text=y.name, row=1, col=1)

    # --- ROW 2: Time Series Plot X (Weather Feature) ---
    fig.add_trace(
        go.Scatter(
            x = x_full,
            y = x[variable], # Use the original (unlagged) X for plotting context
            mode = 'lines',
            name = f'{variable} Full',
            line = dict(color = 'green', width=0.5),
            showlegend=False
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x = x_full[start_idx_focus:end_idx_focus],
            y = x[variable].iloc[start_idx_focus:end_idx_focus],
            mode='lines',
            name=f'{variable} Focus',
            line=dict(color='red', width=1),
            showlegend=False
        ), 
        row=2, col=1
    )
    
    # --- ROW 3: Sliding Window Correlation (SWC) ---
    fig.add_trace(
        go.Scatter(
            x = SWC.index,
            y = SWC,
            mode='lines',
            name='SWC',
            line=dict(color='orange'),
            showlegend=False
        ),
        row=3, col=1
    )

    # Focus point on SWC line
    point_x = x_full[center_idx]
    point_y = SWC.asof(point_x) 

    if not pd.isna(point_y):
        fig.add_trace(go.Scatter(
            x=[point_x],
            y=[point_y],
            mode='markers',
            name='Focus Point',
            marker=dict(color='red', size=10, symbol='circle'),
            showlegend=False
        ), row=3, col=1)
        
    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, row=3, col=1)
    
    # Set Title and Layout
    fig.update_yaxes(title_text='SWC', range=[-1.05, 1.05], row=3, col=1) 
    fig.update_xaxes(title_text='Time', row=3, col=1)

    fig.update_layout(
        title = f'Correlation between {y.name} and {variable} lagged {lag} days: {corr_value:.3f}',
        height=800,
        template="plotly_white",
        margin=dict(t=50) 
    )

    return fig