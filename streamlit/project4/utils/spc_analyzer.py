# streamlit_app/utils/spc_analyzer.py
# Function to performs SPC on a time series DataFrame and returen figure

import numpy as np
import pandas as pd
from scipy.fft import dct, idct
import plotly.graph_objects as go
from typing import Dict, Any, Tuple
import streamlit as st

@st.cache_data()
def satv_anomaly_control(
    df: pd.DataFrame,
    column: str = "temperature_2m",
    dct_cutoff: int = 3,    
    std_dev_multiple: float = 3.0
) -> Tuple[go.Figure, Dict[str, Any]]:
    """
    Computes Seasonally Adjusted Temperature Variations (SATV) using
    DCT-based high-pass filtering, detects anomalies using robust
    statistics, and plots results using Plotly.

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Interactive Plotly figure
    summary : dict
        Summary statistics and outlier information
    """

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame.")

    # Compute SATV using DCT
    series = df[column]
    T = series.values
    N = len(T)

    if not (0 <= dct_cutoff <= N):
        raise ValueError("dct_cutoff must be between 0 and the length of the time series.")

    T_dct = dct(T, type=1, norm="forward")
    T_dct[:dct_cutoff] = 0
    satv_values = idct(T_dct, type=1, norm="forward")

    satv_series = pd.Series(satv_values, index=df.index)

    # Robust statistics (MAD)
    median = satv_series.median()
    mad = (satv_series - median).abs().median()
    robust_std = mad * 1.4826

    upper_satv_limit = median + std_dev_multiple * robust_std
    lower_satv_limit = median - std_dev_multiple * robust_std

    # Outlier detection
    outlier_mask = (satv_series > upper_satv_limit) | (satv_series < lower_satv_limit)
    outliers = df.loc[outlier_mask]

    # Control limits
    seasonal_cycle = series - satv_series
    upper_boundary = seasonal_cycle + upper_satv_limit
    lower_boundary = seasonal_cycle + lower_satv_limit

    # Initialize the figure using go.Figure()
    fig = go.Figure()

    # Add the main data line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=series,
            mode="lines",
            name=f"Original {column}",
            line=dict(color="blue")
        )
    )

    # Control boundaries
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=upper_boundary,
            mode="lines",
            name=f"+{std_dev_multiple} × MAD",
            line=dict(color="red", dash="dash")
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=lower_boundary,
            mode="lines",
            name=f"-{std_dev_multiple} × MAD",
            line=dict(color="red", dash="dash")
        )
    )

    # Add the Anomalies
    fig.add_trace(
        go.Scatter(
            x=outliers.index,
            y=outliers[column],
            mode="markers",
            name="Outliers",
            marker=dict(
                color="gold",
                size=8,
                line=dict(color="black", width=1)
            )
        )
    )

    # Set Title, Grid, and Legend
    fig.update_layout(
        title=(
            f"Outlier Detection, {column}, DCT cutoff = {dct_cutoff}, {std_dev_multiple} × MAD"
        ),
        xaxis_title = "Date",
        yaxis_title = f"{column}"
    )
    
    # Show gridlines
    fig.update_xaxes(showgrid = True, gridwidth = 1, gridcolor = 'lightgray')
    fig.update_yaxes(showgrid = True, gridwidth = 1, gridcolor = 'lightgray')

    # Summary

    summary = {
        "total_observations": len(df),
        "number_of_outliers": int(outlier_mask.sum()),
        "percentage_outliers": float(outlier_mask.mean() * 100),
        "robust_median": float(median),
        "robust_std_estimate": float(robust_std),
        "outlier_data": outliers[[column]]
    }

    return fig, summary

