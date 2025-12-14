# streamlit_app/utils/spc_analyzer.py
# Function to performs SPC on a time series DataFrame and returen figure

# import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
import streamlit as st
import pandas as pd

@st.cache_data()
def calculate_SPC_anomalies(
    df: pd.DataFrame, 
    column: str,
    window: int = 168,  # Default window size in hours
    sigma: float = 3.0  # Default sigma multiplier
) -> tuple[go.Figure, pd.DataFrame, str]:
    """
    Performs SPC on a time series DataFrame.

    Args:
        df (pd.DataFrame) to be analyzed
        colmun(str) 
    Returns
        tuple[go.Figure, pd.DataFrame]: A tuple containing the Plotly figure, 
        and a summary of the analysis.
    """
    df = df.copy()

    # --- SPC part (mean ± 3σ) ---
    # mean_val = df[column].mean()
    # std_val = df[column].std()
    # df['UCL'] = mean_val + 3 * std_val
    # df['LCL'] = mean_val - 3 * std_val

    rolling_mean = df[column].rolling(window=window, min_periods=window).mean()
    rolling_std = df[column].rolling(window=window, min_periods=window).std()
    df['UCL'] = rolling_mean + sigma * rolling_std
    df['LCL'] = rolling_mean - sigma * rolling_std
    
#    df['SPC_Anomaly'] = (df[column] > df['UCL']) | (df[column] < df['LCL'])
    df['SPC_Anomaly'] = (
        (df[column] > df['UCL']) | (df[column] < df['LCL'])
    ) & df['UCL'].notna()

    # Extract anomaly points for separate plotting (where SPC_Anomaly is True)
    anomalies = df[df['SPC_Anomaly'] == True]

    # Initialize the figure using go.Figure()
    fig = go.Figure()

    # Add the main data line
    fig.add_trace(go.Scatter(
        x = df.index,
        y = df[column],
        mode = 'lines',
        name = column,
        line = dict(color = 'blue')
    ))

    # Add the Upper Control Limit (UCL)
    fig.add_trace(go.Scatter(
        x = df.index,
        y = df['UCL'],
        mode = 'lines',
        name = 'UCL (+3σ)',
        line = dict(color = 'red', dash='dash')
    ))

    # Add the Lower Control Limit (LCL)
    fig.add_trace(go.Scatter(
        x = df.index,
        y = df['LCL'],
        mode = 'lines',
        name = 'LCL (-3σ)',
        line = dict(color = 'red', dash='dash')
    ))

    # Add the Anomalies
    fig.add_trace(go.Scatter(
        x = anomalies.index,
        y = anomalies[column],
        mode = 'markers',
        name = 'Anomaly',
        marker = dict(color = 'red', size = 8)
    ))    
    
    # Set Title, Grid, and Legend
    fig.update_layout(
        title = f'{column.capitalize()} - SPC',
        height = 500,
        xaxis_title = "Date",
        yaxis_title = column
    )
    
    # Show gridlines
    fig.update_xaxes(showgrid = True, gridwidth = 1, gridcolor = 'lightgray')
    fig.update_yaxes(showgrid = True, gridwidth = 1, gridcolor = 'lightgray')

    return fig, df[df['SPC_Anomaly']]
