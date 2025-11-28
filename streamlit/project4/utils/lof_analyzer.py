# streamlit_app/utils/lof_analyzer.py
# Function 
# to calculate anomalies according to the Local Outlier Factor method
# to summarize the outliers
# plot the result

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor
import plotly.express as px
from plotly.graph_objects import Figure
from typing import Tuple
import matplotlib.dates as mdates
import streamlit as st

def analyze_LOF_anomalies(
    df_full: pd.DataFrame, 
    feature_col: str, 
    n_neighbors: int, 
    contamination: float
) -> Tuple[Figure, pd.DataFrame]:

    """
    Calcurate anomalies according to the Local Outlier Factor method, 
    summarize of the outliers and plot the result

    Args:
        df_full (pd.DataFrame): The full DataFrame containing the feature to analyze 
                                and all context columns (e.g., 'temperature_2m').
        feature_col (str): The name of the column to run LOF on (e.g., 'precipitation').
        n_neighbors (int): Number of neighbors to use for LOF.
        contamination (float): The proportion of outliers expected in the dataset.

    Returns:
        Tuple[px.Figure, pd.DataFrame]: The plotly Figure and 
                                         a DataFrame summarizing the outliers.
     
    """

    # Filter out potential NaNs for robust LOF calculation
    df_clean = df_full.dropna(subset=[feature_col]).copy()
    
    # Run LOF Analysis
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    
    # LOF expects a 2D array, so reshape the single feature column data
    feature_data = df_clean[feature_col].values.reshape(-1, 1)
    
    # FIX: Pass the numerical-only array (feature_data) to the model, not the whole DataFrame (df_clean).
    pred_labels = lof.fit_predict(X=feature_data)
    
    # Store scores and labels back into the clean DataFrame
    df_clean['LOF_Label'] = pred_labels
    
    # Clip the score to make it more readable/useful for visualization
    df_clean['LOF_Score'] = np.clip(lof.negative_outlier_factor_, -10, 0)
        
    # Store scores and labels back into the clean DataFrame
    df_clean['LOF_Label'] = pred_labels
    df_clean['LOF_Score'] = np.clip(lof.negative_outlier_factor_, -10, 0)

    # Separate Inliers/Outliers and Calculate Baseline
    inliers = df_clean[df_clean['LOF_Label'] == 1]
    outliers = df_clean[df_clean['LOF_Label'] == -1]

    median_baseline = df_clean[feature_col].median()
    mean_baseline = df_clean[feature_col].mean()

    # for Statistical Summary
    total_samples = len(df_clean)
    num_outliers = len(outliers)
    outlier_percentage = (num_outliers / total_samples) * 100
   
    stats_summary = {
        'total_samples': total_samples,
        'num_outliers': num_outliers,
        'outlier_percentage': f'{outlier_percentage:.2f}%' # Format to 2 decimal places
    }

    # Concatenate the inliers and outliers for easy plotting
    df_plot = pd.concat([inliers, outliers])
    df_plot['Type'] = 'Inlier'
    df_plot.loc[df_plot.index.isin(outliers.index), 'Type'] = 'Outlier'
    
    # Create the scatter plot
    fig = px.scatter(
        df_plot,
        x = df_plot.index,
        y = df_plot[feature_col],
        color = 'Type',
        color_discrete_map = {
            'Inlier':'rgba(0, 0, 255, 0.4)',
            'Outlier':'rgba(255, 0, 0, 0.6)'
        },
        title = f'{feature_col.capitalize()} Anomaly Detection using LOF (n_neighbors={n_neighbors}, Contamination={contamination})',
        labels = {'time': 'Date', feature_col:f'{feature_col}'}
    )

    fig.add_hline(
        y = mean_baseline,
        line_dash = 'dot',
        line_color = 'gray',
        annotation_text = 'Mean Baseline',
        annotation_position = 'top right'
    )

    fig.update_traces(
        marker = dict(size = 8),
        opacity = 0.8
    )

    # Update Layout (set title, show grid)
    fig.update_layout(
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        ),
        # xaxis_title='Date', # Re-set labels explicitly if needed
        # yaxis_title=f'{feature_col}',
        # Ensure the x-axis labels are readable (Plotly handles date formatting automatically)
        xaxis = dict(showgrid=True),
        yaxis = dict(showgrid=True),
    )
   
    # Prepare Summary DataFrame
    # Use localized formatting to display clean output
    pd.set_option('display.float_format', '{:.2f}'.format)

    outlier_summary = outliers.copy()

    # Add Baseline Metrics
    outlier_summary['Median_Baseline'] = median_baseline
    outlier_summary['Absolute_Deviation'] = (outlier_summary[feature_col] - mean_baseline).abs()

    # Select and rename final columns for the summary
    summary_cols = {
        feature_col: feature_col.capitalize(),
        'LOF_Score': 'LOF_Score',
        'Median_Baseline': 'Median_Baseline',
        'Absolute_Deviation': 'Absolute_Deviation',
    }
        
    # Final selection and sorting (by LOF_Score for most severe first)
    outlier_summary_final = outlier_summary[summary_cols.keys()] \
        .rename(columns=summary_cols) \
        .sort_values(by='LOF_Score')

    return fig, outlier_summary_final, stats_summary