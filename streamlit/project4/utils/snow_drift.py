#!/usr/bin/env python3
"""
Complete script for calculating annual snow drifting using Tabler (2003)
and visualizing the average directional contributions in a 16-sector wind rose.

Assumptions:
 - Hourly meteorological input is stored in a CSV file 
   (open-meteo-60.57N7.60E1212m.csv).
 - The CSV contains two header sections: metadata in the first few rows and the
   actual data header starting on the fourth row.
 - Hourly temperature, precipitation, wind speed at 10 m, and wind direction at 10 m are provided.
 - Hourly Swe is defined as the precipitation when the temperature is below +1°C.
 - Snow drifting calculations follow Tabler (2003):
     1. Qupot (potential wind-driven transport): summed hourly contributions using u^3.8.
     2. Qspot (snowfall-limited transport): 0.5 * T * Swe.
     3. Srwe (relocated water equivalent): θ * Swe.
     4. If Qupot > Qspot then snowfall controls:
          Qinf = 0.5 * T * Srwe,
        otherwise Qinf = Qupot.
     5. Mean annual snow transport: Qt = Qinf * (1 - 0.14 ** (F/T)).
 - The meteorological data is treated seasonally. In this script the season starts on July 1
   and runs for 12 months (until June 30 of the following year).
 - The rose plot displays the average yearly directional breakdown, and the overall average
   yearly snow transport is shown in tonnes/m (one decimal).
 - The script also computes the necessary fence height for storing the drift.
   For a given fence type, the required height is computed as:
       H = ( (Qt_tonnes) / (Qc/H^2.2) )^(1/2.2)
   where the storage capacity factor (Qc/H^2.2) is taken from Table 3.3:
       - Wyoming: 8.5
       - Slat-and-wire: 7.7
       - Solid: 2.9
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

@st.cache_data(show_spinner=True)
def compute_Qupot(hourly_wind_speeds, dt=3600):
    """
    Compute the potential wind-driven snow transport (Qupot) [kg/m]
    by summing hourly contributions using u^3.8.
    
    Formula:
       Qupot = sum((u^3.8) * dt) / 233847
    """
    total = sum((u ** 3.8) * dt for u in hourly_wind_speeds) / 233847
    return total

@st.cache_data(show_spinner=True)
def sector_index(direction):
    """
    Given a wind direction in degrees, returns the index (0-15)
    corresponding to a 16-sector division.
    """
    # Center the bin by adding 11.25° then modulo 360 and divide by 22.5°
    return int(((direction + 11.25) % 360) // 22.5)

def compute_sector_transport(hourly_wind_speeds, hourly_wind_dirs, dt=3600):
    """
    Compute the cumulative transport for each of 16 wind sectors.
    
    Parameters:
      hourly_wind_speeds: list of wind speeds [m/s]
2      hourly_wind_dirs: list of wind directions [degrees]
      dt: time step in seconds
      
    Returns:
      A list of 16 transport values (kg/m) corresponding to the sectors.
    """
    sectors = [0.0] * 16
    for u, d in zip(hourly_wind_speeds, hourly_wind_dirs):
        idx = sector_index(d)
        sectors[idx] += ((u ** 3.8) * dt) / 233847
    return sectors

@st.cache_data(show_spinner=True)
def compute_snow_transport(T, F, theta, Swe, hourly_wind_speeds, dt=3600):
    """
    Compute various components of the snow drifting transport according to Tabler (2003).
    
    Parameters:
      T: Maximum transport distance (m)
      F: Fetch distance (m)
      theta: Relocation coefficient
      Swe: Total snowfall water equivalent (mm)
      hourly_wind_speeds: list of wind speeds [m/s]
      dt: time step in seconds
      
    Returns:
      A dictionary containing:
         Qupot (kg/m): Potential wind-driven transport.
         Qspot (kg/m): Snowfall-limited transport.
         Srwe (mm): Relocated water equivalent.
         Qinf (kg/m): The controlling transport value.
         Qt (kg/m): Mean annual snow transport.
         Control: Process controlling the transport (wind or snowfall).
    """
    Qupot = compute_Qupot(hourly_wind_speeds, dt)
    Qspot = 0.5 * T * Swe  # Snowfall-limited transport [kg/m]
    Srwe = theta * Swe    # Relocated water equivalent [mm]
    
    if Qupot > Qspot:
        Qinf = 0.5 * T * Srwe
        control = "Snowfall controlled"
    else:
        Qinf = Qupot
        control = "Wind controlled"
    
    Qt = Qinf * (1 - 0.14 ** (F / T))
    
    return {
        "Qupot (kg/m)": Qupot,
        "Qspot (kg/m)": Qspot,
        "Srwe (mm)": Srwe,
        "Qinf (kg/m)": Qinf,
        "Qt (kg/m)": Qt,
        "Control": control
    }

@st.cache_data(show_spinner=True)
def compute_yearly_results(df, T, F, theta):
    """
    Compute the yearly (seasonal) snow transport parameters for every season in the data.
    The season is defined as July 1 of a given year to June 30 of the next year.
    
    Returns a DataFrame with one row per season.
    """
    seasons = sorted(df['season'].unique())
    results_list = []
    for s in seasons:
        season_start = pd.Timestamp(year=s, month=7, day=1)
        season_end = pd.Timestamp(year=s+1, month=6, day=30, hour=23, minute=59, second=59)
        # df_season = df[(df['time'] >= season_start) & (df['time'] <= season_end)]
        df_season = df[(df.index >= season_start) & (df.index <= season_end)]
        if df_season.empty:
            continue
        # Calculate hourly Swe: precipitation counts when temperature < +1°C.
        # df_season = df_season.copy()  # avoid SettingWithCopyWarning
        # df_season['Swe_hourly'] = df_season.apply(
        #     lambda row: row['precipitation (mm)'] if row['temperature_2m (°C)'] < 1 else 0, axis=1)
        # total_Swe = df_season['Swe_hourly'].sum()
        # wind_speeds = df_season["wind_speed_10m (m/s)"].tolist()
        df_season['Swe_hourly'] = df_season.apply(
            lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1)
        total_Swe = df_season['Swe_hourly'].sum()
        wind_speeds = df_season["wind_speed_10m"].tolist()
        result = compute_snow_transport(T, F, theta, total_Swe, wind_speeds)
        result["season"] = f"{s}-{s+1}"
        results_list.append(result)
    return pd.DataFrame(results_list)

@st.cache_data(show_spinner=True)
def compute_average_sector(df):
    """
    Compute the average directional breakdown (sectors) over all seasons.
    The function groups the data by season and computes the sector contributions
    for each season, then returns the mean across seasons.
    """
    sectors_list = []
    for s, group in df.groupby('season'):
        group = group.copy()
        group['Swe_hourly'] = group.apply(
            lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1)
        ws = group["wind_speed_10m"].tolist()
        wdir = group["wind_direction_10m"].tolist()
        # group['Swe_hourly'] = group.apply(
        #     lambda row: row['precipitation (mm)'] if row['temperature_2m (°C)'] < 1 else 0, axis=1)
        # ws = group["wind_speed_10m (m/s)"].tolist()
        # wdir = group["wind_direction_10m (°)"].tolist()
        sectors = compute_sector_transport(ws, wdir)
        sectors_list.append(sectors)
    avg_sectors = np.mean(sectors_list, axis=0)
    return avg_sectors

@st.cache_data(show_spinner=True)
def plot_rose2(avg_sector_values, overall_avg):
    """
    Create a Plotly polar (wind rose) plot showing the average directional breakdown.

    Parameters:
      avg_sector_values: list or array of 16 average transport values (kg/m) for the sectors.
      overall_avg: overall average yearly snow transport (Qt in kg/m).
    """
    # --- Data Preparation ---
    num_sectors = 16
    sector_width_deg = 360 / num_sectors
    
    # 1. Compute bin CENTERS in degrees.
    # The sectors are 0-22.5, 22.5-45, ..., 337.5-360.
    # The center of the first sector (N) is at 11.25 degrees.
    # Plotly's Barpolar 'theta' expects degrees for the bar center.
    sector_centers_deg = np.arange(0, 360, sector_width_deg) + sector_width_deg / 2
    
    # The first sector (index 0) is N (from 348.75 to 11.25), but we need the data 
    # to start corresponding to the angular axis labels (N, NNE, ...).
    # Since the first angle in sector_centers_deg is 11.25, which corresponds to NNE 
    # in the standard angular axis setup, we need to cyclically shift the data 
    # so the 'N' data is centered at the correct plot angle.
    # We want N (index 0) to appear at the North position (or near 0/360 degrees).
    # Since Plotly centers the first bar at the first theta value (11.25), and 
    # the Matplotlib code implicitly used 0 as N, we will use a small shift 
    # to align the sector values with the correct angular centers for the labels.
    
    # Convert the sector values from kg/m to tonnes/m
    avg_sector_values_tonnes = np.array(avg_sector_values) / 1000.0
    
    # The directions are: ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
    #                      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    
    # --- Plotly Figure Creation ---
    
    # Use go.Barpolar. Note: Plotly expects degrees for theta by default.
    fig = go.Figure(go.Barpolar(
        r=avg_sector_values_tonnes,
        theta=sector_centers_deg,
        width=sector_width_deg, # Width is also in degrees
        marker_color="cornflowerblue", # Use a color
        marker_line_color="black",
        marker_line_width=1,
        opacity=0.8,
        name='Avg Snow Transport'
    ))

    # Convert overall average from kg/m to tonnes/m and format with one decimal.
    overall_tonnes = overall_avg / 1000.0

    # --- Layout Configuration (The crucial part for rose plots) ---
    fig.update_layout(
        # Set the title
        # title={
        #     # 'text': f"Average Directional Distribution of Snow Transport<br>Overall Average Q_t: {overall_tonnes:,.1f} tonnes/m",
        #     'y':0.95,
        #     'x':0.5,
        #     'xanchor': 'center',
        #     'yanchor': 'top'
        # },
        # Configure the polar coordinate system
        polar=dict(
            # 1. Radial Axis (r-axis)
            radialaxis=dict(
                # Title for the radial axis
                title=dict(text="Average Transport (tonnes/m)", font=dict(size=12)),
                visible=True, # Keep radial grid lines/ticks visible
                # Set min/max range based on the data to avoid padding, or fix max for comparison
                range=[0, avg_sector_values_tonnes.max() * 1.1], 
                tickformat=".1f" # Format radial ticks
            ),
            # 2. Angular Axis (theta-axis)
            angularaxis=dict(
                # **Set North to the top (0 degrees)**
                direction="clockwise", # **Set clockwise direction**
                rotation=90, # **Rotate the axis so North (0/360) is at the top (90 degrees)**
                
                # Set custom tick positions and labels
                tickvals=np.arange(0, 360, sector_width_deg), # Tick positions at the sector boundaries
                ticktext=directions, # Use your list of directions as labels
                
                # Make grid lines visible and control their properties
                showgrid=True,
                gridcolor="lightgrey",
                
                # Hide the starting and ending ticks if you prefer a cleaner look
                # showline=True,
                # linecolor='black'
            )
        ),
        # Remove background/border if desired
        paper_bgcolor='white',
        plot_bgcolor='white',
        # Set the size of the figure
        height=700,
        width=700
    )

    return fig

@st.cache_data(show_spinner=True)
def compute_fence_height(Qt, fence_type):
    """
    Calculate the necessary effective fence height (H) for storing a given snow drift.
    
    Parameters:
      Qt : float
           The calculated mean annual snow transport (drift) in kg/m.
      fence_type : str
           The fence type. Supported types are:
           "Wyoming", "Slat-and-wire", and "Solid".
    
    Returns:
      H : float
          The necessary effective fence height (in meters).
    
    Calculation:
      1. Convert Qt from kg/m to tonnes/m (divide by 1000).
      2. Use the storage capacity factor for the selected fence type:
             - Wyoming: 8.5
             - Slat-and-wire: 7.7
             - Solid: 2.9
      3. Calculate H = ( (Qt_tonnes) / (factor) )^(1/2.2)
    """
    Qt_tonnes = Qt / 1000.0
    if fence_type.lower() == "wyoming":
        factor = 8.5
    elif fence_type.lower() in ["slat-and-wire", "slat and wire"]:
        factor = 7.7
    elif fence_type.lower() == "solid":
        factor = 2.9
    else:
        raise ValueError("Unsupported fence type. Choose 'Wyoming', 'Slat-and-wire', or 'Solid'.")
    
    H = (Qt_tonnes / factor) ** (1 / 2.2)
    return H

