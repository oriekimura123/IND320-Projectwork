## utils/sarimax.py
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
import warnings
from typing import List, Tuple
import streamlit as st

@st.cache_data(show_spinner=True)
def run_SARIMAX_model(
    df: pd.DataFrame,
    target: str,
    exog_vars: List[str],
    train_end: pd.Timestamp,
    order: tuple,
    seasonal_order: tuple,
    freq: str
) -> Tuple[go.Figure, list]:

    warnings_list = []
    df = df.copy()

    # ---- Ensure datetime index ----
    df.index = pd.to_datetime(df.index).tz_localize(None)

    # ---- Resampling strategy ----
    agg_map = {}
    for col in df.columns:
        if any(k in col for k in ["temperature", "wind"]):
            agg_map[col] = "mean"
        else:
            agg_map[col] = "sum"

    freq_map = {
        "Hourly": "H",
        "Daily": "D",
        "Weekly": "W",
        "Monthly": "M"
    }

    seasonal_period_map = {
        "Hourly": 24, # Daily cycle for Hourly data
        "Daily": 7,    # Weekly cycle for Daily data
        "Weekly": 52,   # Yearly cycle for Weekly data
        "Monthly": 12   # Yearly cycle for Monthly data
    }

    df = df.resample(freq_map[freq]).agg(agg_map)

    s = seasonal_period_map.get(freq)
    if s is None:
        # Fallback/Error handling if an unknown frequency is passed
        raise ValueError(f"Unknown frequency option: {freq}")

    P, D, Q, s_placeholder = seasonal_order 
    final_seasonal_order = (P, D, Q, s)

    # ---- Build combined dataframe ----
    cols = [target] + exog_vars if exog_vars else [target]
    df_model = df[cols].dropna()

    y = df_model[target]
    X = df_model[exog_vars] if exog_vars else None

    # ---- Train/Test split  ----
    y_train = y.loc[:train_end]
    X_train = X.loc[:train_end] if X is not None else None

    # ---- Optional scaling of exogenous ----
    if X is not None:
        scaler = StandardScaler()
        X_scaled = pd.DataFrame(
            scaler.fit_transform(X),
            index=X.index,
            columns=X.columns
        )
        X_train = X_scaled.loc[:train_end]
        X_full = X_scaled
    else:
        X_full = None

    # ---- Safety check ----
    if X_train is not None:
        assert len(y_train) == len(X_train), \
            f"Shape mismatch: y={y_train.shape}, X={X_train.shape}"

    # ---- Fit SARIMAX ----
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            model = sm.tsa.statespace.SARIMAX(
                y_train,
                exog=X_train,
                order=order,
                seasonal_order=final_seasonal_order,
#                seasonal_order=seasonal_order,
                trend=None,
                enforce_stationarity=False,
                enforce_invertibility=False
            )

            result = model.fit(disp=False)

            for warn in w:
                warnings_list.append(str(warn.message))

    except Exception as e:
        raise RuntimeError(f"SARIMAX failed: {e}")

    # ---- Forecast ----
    # ---- In-sample prediction (fitted values) ----
    pred_in = result.get_prediction(
        start=y_train.index[0],
        end=y_train.index[-1],
        exog=X_train
    )

    # ---- Out-of-sample forecast ----
    H = len(y) - len(y_train)
    forecast_index = y.index[y.index > y_train.index[-1]][:H]
    X_forecast = X_full.loc[forecast_index] if X_full is not None else None
    assert len(forecast_index) == H
    if X_forecast is not None:
        assert len(X_forecast) == H

    pred_out = result.get_forecast(
        steps=H,
        exog=X_forecast
    )

    pred_in_mean = pred_in.predicted_mean
    pred_out_mean = pred_out.predicted_mean

    ci_in = pred_in.conf_int()
    ci_out = pred_out.conf_int()

    if "temperature_2m" not in target.lower():
        pred_in_mean = pred_in_mean.clip(lower=0)
        pred_out_mean = pred_out_mean.clip(lower=0)

        ci_in.iloc[:, 0] = ci_in.iloc[:, 0].clip(lower=0)
        ci_out.iloc[:, 0] = ci_out.iloc[:, 0].clip(lower=0)

    # ---- Plot ----
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=y.index,
        y=y,
        name="Observed",
        mode="lines"
    ))

    fig.add_trace(go.Scatter(
        x=pred_in_mean.index,
        y=pred_in_mean,
        name="Fitted",
        mode="lines",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=pred_out_mean.index,
        y=pred_out_mean,
        name="Forecast",
        mode="lines",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=ci_out.index,
        y=ci_out.iloc[:, 0],
        showlegend=False,
        line=dict(width=0)
    ))

    fig.add_trace(go.Scatter(
        x=ci_out.index,
        y=ci_out.iloc[:, 1],
        fill="tonexty",
        name="Confidence Interval",
        fillcolor="rgba(255,0,0,0.15)",
        line=dict(width=0)
    ))

    fig.add_shape(
        type="line",
        x0=y_train.index[-1],
        x1=y_train.index[-1],
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="black", dash="dot")
    )

    fig.update_layout(
        title=f"SARIMAX Forecast — {target}",
        xaxis_title="Time",
        yaxis_title=str(target),
        height=600
    )

    return fig, warnings_list
