# streamlit_app/utils/spc_analyzer.py
# Function to perform STL_decomposition and returen figure

import numpy as np
# import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL
import pandas as pd
import streamlit as st

def analyze_decompose_STL(
    df: pd.DataFrame,
    area: str = 'NO3',
    prod_group: str = 'hydro',
    period: int = 24,           # Sensible default: 24 hours (daily seasonality)
    seasonal_smoother: int = 13, # Sensible default: odd number > 7, controls seasonal smoothness
    trend_smoother: int = 501,  # Sensible default: large odd number for annual trend
    robust: bool = True,        # Sensible default: True (robust to outliers/anomalies)
    prod_col: str = 'quantitykwh'
):
    """
    Performs STL decomposition (LOESS) on electricity production data and plots the result.

    Args:
        df (pd.DataFrame): The full DataFrame loaded from elbub JSON.
        area (str): Electricity price area (e.g., 'NO1').
        prod_group (str): Production group (e.g., 'hydro').
        period (int): Length of the seasonal cycle (e.g., 24 for daily, 24*7 for weekly).
        seasonal_smoother (int): Odd span (window size) for seasonal smoothing (odd, typically < period).
        trend_smoother (int): Odd span for trend smoothing (must be odd).
        robust (bool): If True, uses robust fitting (less sensitive to outliers).
        prod_col (str): The name of the production column.

    Returns:
        plt.Figure: The Matplotlib Figure object containing the decomposition plot.
    """
    
    # Price Area filter
    # area_filter = df['priceArea'].str.strip() == area 
    
    # prod_group filter
    # prod_group_filter = df['productionGroup'].str.strip() == prod_group
    
    # Apply the combined filter
    # df_filtered = df[area_filter & prod_group_filter].copy()

    df = df.rename(columns={'date': 'time'})
    df = df.set_index('time')
    df_filtered = df.copy()

    # Check for emptiness
    if df_filtered.empty:
        # Raise an informative error based on the original input
        raise ValueError(f"No data found for Area: {area} and Group: {prod_group}. Check data values.")
    
    # Ensure the Series is continuous and sorted
    series = df_filtered[prod_col].sort_index()
    # series.index = pd.to_datetime(series.index)

    # Set the end date. We can use the max date or a slightly later date.
    first_date = series.index.min()
    last_date = series.index.max()

    # Check if the series is long enough
    min_length = period + 1
    if len(series) < min_length:
        raise ValueError(f"Series too short for period {period}. Requires at least {min_length} observations.")
    
    try:
        # The key parameters match the function arguments:
        res = STL(
            series, 
            period=period, 
            seasonal=seasonal_smoother, 
            trend=trend_smoother, 
            robust=robust
        ).fit()
    except Exception as e:
        print(f"STL decomposition failed. Check period and smoother spans: {e}")
        return None

    # Plot the Decomposition
    # Create a 4-row subplot structure with shared X-axis
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        # Define titles for each subplot
        subplot_titles=['Observed', 'Trend', 'Seasonal', 'Residual', 'Observed']
    )

    # Plot Observed
    fig.add_trace(
        go.Scatter(x = res.observed.index, y = res.observed.values, mode = 'lines', line = dict(color='blue')),
        row = 1,
        col = 1
    )

    # Plot Trend
    fig.add_trace(
        go.Scatter(x = res.trend.index, y = res.trend.values, mode = 'lines', line = dict(color='pink')),
        row = 2,
        col = 1
    )

    # Plot Seasonal
    fig.add_trace(
        go.Scatter(x = res.seasonal.index, y = res.seasonal.values, mode = 'lines', line = dict(color='orange')),
        row = 3,
        col = 1
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, row=3, col=1)

    # Plot Residual
    fig.add_trace(
        go.Scatter(x = res.resid.index, y = res.resid.values, mode = 'lines', line = dict(color='green')),
        row = 4,
        col = 1
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, row=4, col=1)

    # Customizing the Plot Title
    fig.update_layout(
        title={
            'text': f'STL Decomposition of {prod_group} production in {area}, 2021,<br>' 
            f'Parameters: Period={period}, S_span={seasonal_smoother}, '
            f'T_span={trend_smoother}, Robust={robust}',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        height=800,  # Set height for 4 stacked plots
        showlegend=False,
        margin=dict(t=120)
    )
    
    # Add parameter summary text

    # Apply gridlines
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGrey',
        range=[first_date, last_date], 
        type='date'
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='LightGrey'
    )
    
    return fig