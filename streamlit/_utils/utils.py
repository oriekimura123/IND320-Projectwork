import streamlit as st
import pandas as pd
from datetime import date


MIN_DATE = date(2021, 1, 1)
MAX_DATE = date(2024, 12, 31)

def get_area_filtered_data(df: pd.DataFrame, selected_area: str) -> pd.DataFrame:
    """
    Filters a DataFrame by the 'area' column. Assumes the column is named 'area'.
    
    Args:
        df: The raw Pandas DataFrame loaded from MongoDB.
        selected_area: The specific area/zone name selected by the user.
        
    Returns:
        The filtered DataFrame.
    """
    # CRITICAL: Change this constant if the area column name is different in your database
    AREA_COL_NAME = 'pricearea' 
    
    if AREA_COL_NAME not in df.columns:
        return df 
    
    if selected_area is None:
        return df
    
    # Perform the filtering based on the user's selection
    df_filtered = df[df[AREA_COL_NAME] == selected_area]
    
    if df_filtered.empty:
        st.warning(f"No data found for the selected area: {selected_area}")
        return df
        
    return df_filtered

def initialize_session_state():
    """Initialize all session-state keys in one place (idempotent)."""
if "last_pin" not in st.session_state:
    st.session_state.last_pin = [63.5130, 9.8087]

if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = None

# selection lock and defaults
if "filtering_confirmed" not in st.session_state:
    st.session_state.filtering_confirmed = False
    st.session_state.selected_area = "NO3"
    st.session_state.selected_energy_datatype = "Production data"
    st.session_state.date_range_1_2 = (MIN_DATE, MAX_DATE)
    st.session_state.date_range_3 = (MIN_DATE, MAX_DATE)

if "sidebar_context_blocks" not in st.session_state:
    st.session_state.sidebar_context_blocks = []


def draw_analysis_context_sidebar():
    """Draw the persistent analysis parameters in the sidebar.

    Note: This function reads `st.session_state.sidebar_context_blocks` which
    pages should set *before* calling this function for immediate display.
    """
# st.sidebar.header("Current Selection")

# area = st.session_state.get("selected_area", "N/A")
# data_type = st.session_state.get("selected_energy_datatype", "N/A")

# st.sidebar.markdown("**Area (Locked):**")
# st.sidebar.info(f"**{area}**")

# st.sidebar.markdown("**Energy Data Type (Locked):**")
# st.sidebar.info(f"**{data_type}**")

# st.sidebar.markdown("---")
# st.sidebar.subheader("Analysis Time Windows")

# context_blocks = st.session_state.get("sidebar_context_blocks", [])
# if context_blocks:
#     for title, text_content in context_blocks:
#         st.sidebar.markdown(f"**{title}**")
#         st.sidebar.text(text_content)
#     else:
#         st.sidebar.text("No specific analysis period selected.")