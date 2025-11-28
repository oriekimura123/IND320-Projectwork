## utils/sarimax.py
import plotly.graph_objects as go
import pandas as pd
import statsmodels.api as sm
import streamlit as st
from typing import List
from datetime import date
import numpy as np
import warnings

@st.cache_data(show_spinner=True)
def run_SARIMAX_model(
    df: pd.DataFrame,
    plott_start_date: date,
    end_train: pd.Timestamp,
    target: str,
    exog_vars: List,
    freq: str = "Daily"
) -> tuple[go.Figure, list]: 

    # Ensure index is datetime and tz-naive
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
            df.set_index("time", inplace=True)
        else:
            df.index = pd.to_datetime(df.index).tz_localize(None)
    else:
        df.index = df.index.tz_localize(None)

    # Set seasonality
    if freq == "Hourly":
        df = df.resample("H").sum()
        season = 24     # dayly seasonality
    elif freq == "Daily":
        df = df.resample("D").sum()
        season = 7     # weekly seasonality
    elif freq == "Weekly":
        df = df.resample("W").sum()
        season = 52    # annual-ish seasonal cycle for weekly
    elif freq == "Monthly":
        df = df.resample("M").sum()
        season = 12    # yearly seasonal cycle

    start_ts = pd.to_datetime(plott_start_date)
    end_train_ts = pd.to_datetime(end_train)

    # Prepare exogenous
    exog_train = df.loc[:end_train_ts, exog_vars] if exog_vars else None
    exog_full = df.loc[:, exog_vars] if exog_vars else None

    captured_warnings = []

    # --- WARNING CAPTURE BLOCK ---
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", UserWarning)
        
        # Fit model on training subset
        try:
            mod = sm.tsa.statespace.SARIMAX(
                df[target].loc[:end_train_ts],
                exog=exog_train,
                trend="c",
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, season)
            )
            res = mod.fit(disp=False)
        except Exception as e:
            st.error(f"Error: SARIMAX Fit model on training subset: {e}")
            return go.Figure()
        
        # Full-sample filter for consistent one-step predictions
        try:
            mod_full = sm.tsa.statespace.SARIMAX(
                df[target], exog=exog_full, trend="c", order=(1, 1, 1), seasonal_order=(1, 1, 1, season)
            )
            res_full = mod_full.filter(res.params)
        except Exception as e:
            st.error(f"Error fitting SARIMAX: {e}")
            return go.Figure()

        for warning in w:
            captured_warnings.append(str(warning.message))

    pred = res_full.get_prediction()
    pred_ci = pred.conf_int()
    pred_mean = pred.predicted_mean

    pred_dyn = res_full.get_prediction(dynamic=end_train_ts)
    pred_dyn_ci = pred_dyn.conf_int()
    pred_dyn_mean = pred_dyn.predicted_mean

    # --- APPLY NON-NEGATIVITY FOR ONE-STEP OUTPUTS ---
    pred_mean = pred_mean.clip(lower=0)
    pred_ci[pred_ci.columns[0]] = pred_ci[pred_ci.columns[0]].clip(lower=0)

    # --- APPLY NON-NEGATIVITY FOR DYNAMIC OUTPUTS ---
    dyn_lower_col = pred_dyn_ci.columns[0]
    dyn_upper_col = pred_dyn_ci.columns[1]

    pred_dyn_mean = pred_dyn_mean.clip(lower=0)
    pred_dyn_ci[dyn_lower_col] = pred_dyn_ci[dyn_lower_col].clip(lower=0)
    pred_dyn_ci[dyn_upper_col] = pred_dyn_ci[dyn_upper_col].clip(lower=0)

    # Guarantee ordering: lower ≤ mean ≤ upper
    pred_ci[pred_ci.columns[0]] = np.minimum(pred_ci[pred_ci.columns[0]], pred_mean)
    pred_ci[pred_ci.columns[1]] = np.maximum(pred_ci[pred_ci.columns[1]], pred_mean)

    pred_dyn_ci[dyn_lower_col] = np.minimum(pred_dyn_ci[dyn_lower_col], pred_dyn_mean)
    pred_dyn_ci[dyn_upper_col] = np.maximum(pred_dyn_ci[dyn_upper_col], pred_dyn_mean)

    # Filter for plotting window
    df_plot = df.loc[start_ts:]
    pred_mean_f = pred_mean.loc[start_ts:]
    pred_ci_f = pred_ci.loc[start_ts:]
    # pred_dyn_mean_f = pred_dyn_mean.loc[start_ts:]
    # pred_dyn_ci_f = pred_dyn_ci.loc[start_ts:]
    pred_dyn_mean_f = pred_dyn_mean.loc[end_train_ts:]
    pred_dyn_ci_f = pred_dyn_ci.loc[end_train_ts:]

    lower, upper = pred_ci_f.columns
    dl, du = pred_dyn_ci_f.columns

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=df_plot.index, y=df_plot[target], mode="lines", name="Observed", marker=dict(color="blue"))
    )

    # One-step CI
    fig.add_trace(
        go.Scatter(x=pred_ci_f.index, y=pred_ci_f[upper], mode="lines", line=dict(width=0), showlegend=False))
    fig.add_trace(
        go.Scatter(
            x=pred_ci_f.index,
            y=pred_ci_f[lower],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(255,0,0,0.1)",
            name="1-step CI",
        )
    )

    fig.add_trace(go.Scatter(x=pred_mean_f.index, y=pred_mean_f, mode="lines", name="1-step forecast", line=dict(color="red", width=2, dash="dash")))

    # Dynamic CI
    fig.add_trace(go.Scatter(x=pred_dyn_ci_f.index, y=pred_dyn_ci_f[du], mode="lines", line=dict(width=0), showlegend=False))
    fig.add_trace(
        go.Scatter(
            x=pred_dyn_ci_f.index,
            y=pred_dyn_ci_f[dl],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(0,255,0,0.1)",
            name="Dynamic CI",
        )
    )

    fig.add_trace(go.Scatter(x=pred_dyn_mean_f.index, y=pred_dyn_mean_f, mode="lines", name="Dynamic forecast", line=dict(color="green", width=2, dash="dash")))

    fig.update_layout(title=f"SARIMAX Model — {target} — exog={exog_vars}", height=600, xaxis_title="Date", yaxis_title="Quantity (kWh)")
    fig.update_layout(legend=dict(yanchor="bottom", y=0.99, xanchor="auto", x=0.99))

    return fig, captured_warnings 