# streamlit_app/utils/lof_analyzer.py
# Function 
# to calculate anomalies according to the Local Outlier Factor method
# to summarize the outliers
# plot the result

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Any
import matplotlib.dates as mdates

def analyze_LOF_anomalies(
    df_full: pd.DataFrame, 
    feature_col: str, 
    n_neighbors: int, 
    contamination: float
) -> Tuple[plt.Figure, pd.DataFrame]:

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
        Tuple[plt.Figure, pd.DataFrame]: The generated matplotlib Figure and 
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

    # Generate Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the inliers using the time index
    ax.plot(inliers['time'], inliers[feature_col], 'o', alpha=0.5, label='Inlier')

    # Plot the outliers using the time index
    ax.plot(outliers['time'], outliers[feature_col], 'o', color='red', label='Outlier')
 
    # Plot Aesthetics
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d')) 
    fig.autofmt_xdate() # Automatically rotates and aligns the date labels

    ax.set_xlabel('Date')
    ax.set_ylabel(f'{feature_col}') 
    ax.axhline(mean_baseline, color='gray', linestyle=':', label='Mean Baseline')
    ax.legend(loc='upper right')
    ax.set_title(f'{feature_col.capitalize()} Anomaly Detection using LOF (n_neighbors={n_neighbors}, Contamination={contamination})')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout() # Adjust layout to prevent clipping

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