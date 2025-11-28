# streamlit_app/utils/spc_analyzer.py
# Function to performs SPC on a time series DataFrame and returen figure

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import pandas as pd

def calculate_SPC_anomalies(
      df: pd.DataFrame, 
      column: str
) -> plt.Figure:
    """
    Performs SPC on a time series DataFrame.

    Args:
        df (pd.DataFrame) to be analyzed
        colmun(str) 
    Returns
        Matplotlib figure.
    """
    df = df.copy()

    # Ensure datetime index
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")

    # --- SPC part (mean ± 3σ) ---
    mean_val = df[column].mean()
    std_val = df[column].std()
    df["UCL"] = mean_val + 3 * std_val
    df["LCL"] = mean_val - 3 * std_val
    df["SPC_Anomaly"] = (df[column] > df["UCL"]) | (df[column] < df["LCL"])

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df[column], label=column, color="blue")
    ax.plot(df.index, df["UCL"], "r--", label="UCL (+3σ)")
    ax.plot(df.index, df["LCL"], "r--", label="LCL (-3σ)")
    ax.scatter(df.index[df["SPC_Anomaly"]], df[column][df["SPC_Anomaly"]], color="red", label="Anomaly")
    ax.set_title(f"{column.capitalize()} - SPC")
    ax.legend()
    ax.grid(True)

    return fig, df[df["SPC_Anomaly"]]
