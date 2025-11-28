import streamlit as st
import pandas as pd

if 'df_display_data' not in st.session_state:
    # Default to None initially. The code below will set it to the first available metric column 
    st.session_state['df_display_data'] = pd.DataFrame()

if 'selected_column' not in st.session_state:
    # Default to None initially. The code below will set it to the first available metric column 
    st.session_state['selected_column'] = None

selected_year = 2021

st.title("Weather data analysys")
st.subheader(f"Weather Data : {selected_year}, area : {st.session_state['selected_area']}")

tab1, tab2 = st.tabs(["Outelier/SPC analysis", "Anomaly/LOF analysis"])

with tab1:
    st.subheader("Outelier/SPC analysis")

    from utils.spc_analyzer import calculate_SPC_anomalies

    # Run analysis
    SPC_fig, SPC_anomalies = calculate_SPC_anomalies(
        st.session_state['df_display_data'], 
        column = st.session_state['selected_column'])

    # --- Display Results ---
    st.plotly_chart(SPC_fig, use_container_width=True)
    st.dataframe(SPC_anomalies)

with tab2:
    st.subheader("Anomaly/LOF analysis")

    from utils.lof_analyzer import analyze_LOF_anomalies

    LOF_neighbors=20
    LOF_contamination=0.01

    LOF_fig, LOF_summary, LOF_stats = analyze_LOF_anomalies(
        st.session_state['df_display_data'], 
        feature_col = st.session_state['selected_column'], 
        n_neighbors = LOF_neighbors, 
        contamination = LOF_contamination)

    st.pyplot(LOF_fig)
    st.write("Statistics:", LOF_stats)
    st.write("Outlier Summary Head:\n", LOF_summary.head())