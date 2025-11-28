# streamlit_app/utils/spc_analyzer.py
# Function to perform STL_decomposition and returen figure

import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
# from typing import Tuple, Dict, Any
import pandas as pd

def analyze_decompose_STL(
    df: pd.DataFrame,
    area: str = 'NO3',
    prod_group: str = 'hydro',
    period: int = 24,           # Sensible default: 24 hours (daily seasonality)
    seasonal_smoother: int = 13, # Sensible default: odd number > 7, controls seasonal smoothness
    trend_smoother: int = 501,  # Sensible default: large odd number for annual trend
    robust: bool = True,        # Sensible default: True (robust to outliers/anomalies)
    prod_col: str = 'quantitykwh'
) -> plt.Figure:
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
    fig = plt.figure(figsize=(10, 15))
    fig = res.plot(fig)
    
    for ax in fig.axes:
        # Rotate x-axis labels by 45 degrees for better readability
        ax.tick_params(axis='x', rotation=45)
        
    # Customizing the Plot Title for clarity
    fig.suptitle(
        f'STL Decomposition of {prod_group} Production in {area}, 2021', 
        fontsize=10, 
        y=1.02
    )
    
    # Add parameter summary to the plot
    fig.text(0.02, 0.03, 
             f'P={period}, S_span={seasonal_smoother}, T_span={trend_smoother}, Robust={robust}', 
             fontsize=10, transform=fig.transFigure)
    
    plt.tight_layout()
    plt.tight_layout(rect=[0, 0.05, 1, 0.98])
    
    return fig