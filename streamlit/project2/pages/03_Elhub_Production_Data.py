import streamlit as st
import pandas as pd

import pymongo

import plotly.express as px

import calendar

from datetime import datetime, timedelta

mongo_uri = st.secrets["mongo"]["uri"] 

MONGO_DATABASE = "elhub_data"
MONGO_COLLECTION = "production_data_hourly"

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()

# Pull data from the collection.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=600)
def load_Mongodb_data():
    db = client[MONGO_DATABASE]
    collection = db[MONGO_COLLECTION]
    items = collection.find()
    items = list(items)
    
    df = pd.DataFrame(items)
    return df

# The data is now a flat list of documents
df_data_raw = load_Mongodb_data()

# Page configuration
st.title("Elhub Production Data in 2021")
st.write("This page will visualize Elhub production data.")

col1, col2 = st.columns(2)

# colors in charts
COLOR_MAP = {
    "hydro": "#1f77b4",   # blue
    "wind": "#17becf",    # cyan/light blue
    "thermal": "#7f7f7f", # gray
    "solar": "#e377c2",   # pink
    "other": "#2ca02c"    # green
}

with col1:
    ## --- Page configuration for col1
    st.header("Price Area Pie Chart (production group)")
    st.write("Use radio buttons to select a price area and display a pie chart.")
    
    radio_columns = ['NO1', 'NO2', 'NO3', 'NO4', 'NO5']
    options_columns = ["All Areas"] + radio_columns
    
    selected_pricearea = st.radio("Select Price Area", options_columns, index=0)
    st.write(f"You selected: {selected_pricearea}")
    
    # Logic for Pie Chart (Column 1)
    if selected_pricearea == "All Areas":
        title_text = "Overall Production Distribution (All Areas)"
        df_pie = df_data_raw.groupby('productiongroup')['quantitykwh'].sum().reset_index()
    else:
        df_filtered = df_data_raw[df_data_raw['pricearea'] == selected_pricearea]
        df_pie = df_filtered.groupby('productiongroup')['quantitykwh'].sum().reset_index()
        title_text = f"Production Distribution in {selected_pricearea}"

    # --- Display Pie Chart (Plotly) ---
    if not df_pie.empty and df_pie['quantitykwh'].sum() > 0:
        total_kwh = df_pie['quantitykwh'].sum()
        
        fig_pie = px.pie(
            df_pie,
            names='productiongroup',
            values='quantitykwh',
            color_discrete_map=COLOR_MAP,
            title=f"{title_text} (Total kwh: {total_kwh:,.0f})"
        )
        
        fig_pie.update_traces(
            textinfo='percent+label', 
            rotation=180,
            marker=dict(line=dict(color='#000000', width=1))
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        st.caption("Data source: MongoDB")
    else:
        st.warning(f"No production data found for {selected_pricearea}.")

with col2:
    ## --- Page configuration for col2
    st.header("Production Group Line Chart (month)")
    st.write("Use pills to select which production group to include and a selection element of your choice to select a month." \
    "Combine the price area, production groups and month, and display a line chart.")
    
    # Convert to Tz-naive datetime64[ns]
    df_data_raw['starttime'] = pd.to_datetime(
        df_data_raw['starttime'], 
        errors='coerce',
        utc=True, # Forces conversion to UTC time before making it naive
        infer_datetime_format=True # Optional: helps Pandas find the ISO format
    ).dt.tz_localize(None)# Forces the type to NumPy datetime64[ns]

    #  Make a list of values in the 'productiongroup' column for the pills
    pill_alternativ = ['hydro', 'wind','thermal', 'solar', 'other']
    selected_productiongroups = st.pills("Select Production Group",pill_alternativ, selection_mode="multi")

    #  Make a list of values in the name of months for the selectbox
    month_options = ["All months"] + list(calendar.month_name[1:])
    selected_month = st.selectbox("Filter to a Single Month", month_options, index=0, width=200)
    
    # apply filters in pandas
    df_filtered = df_data_raw.copy()
    df_filtered['date'] = df_filtered['starttime'].dt.floor('D')

    # Logic for Line Chart (Column 2)
    if selected_pricearea != "All Areas":
        df_filtered = df_filtered[df_filtered['pricearea'] == selected_pricearea]

    if selected_productiongroups:
        df_filtered = df_filtered[df_filtered['productiongroup'].isin(selected_productiongroups)]

    if selected_month != "All months":
        import calendar
        month_number = list(calendar.month_name).index(selected_month)
        df_filtered = df_filtered[df_filtered['starttime'].dt.month == month_number]
    
    # aggregate daily per productiongroup
    df_plot_pd = (
        df_filtered
        .groupby(['date', 'productiongroup'], as_index=False)['quantitykwh']
        .sum()
    )

    # --- Display Line Chart (Plotly) ---
    if not df_plot_pd.empty:
        title = f"Production per Group – {selected_month} 2021 – Area: {selected_pricearea if selected_pricearea != 'All Areas' else 'All Areas in Norway'}"
        fig_line = px.line(
            df_plot_pd,
            x="date",
            y="quantitykwh",
            color="productiongroup",
            color_discrete_map=COLOR_MAP,
            title=title,
            labels={"quantitykwh": "Production (kWh)", "starttime": "Date"},
        )
  
        # Format the X-axis ticks to show Month and Year
        fig_line.update_xaxes(
            tickformat="%d %b %Y"
        )

        st.plotly_chart(fig_line, use_container_width=True)
        st.caption("Data displays simulated monthly production trends across all price areas and groups.")
    else:
        st.warning("No production data available for the selected filters.")

with st.expander("See explanation"):
    st.write('''
        “The chart above displays data retrieved from the PRODUCTION_PER_GROUP_MBA_HOUR endpoint of the Elhub API 
             (via api.elhub.no/energy-data) which provides hourly production figures by price-area and production group.
             Data extraction is performed via API calls, then stored locally in a Apache Cassandra database. 
             The data is aggregated and cleaned using Spark, and the processed, plot-ready datasets are stored in remote MongoDB Atlas. 
             Finally, this Streamlit app loads the data from MongoDB Atlas to produce interactive visualizations.” 
    ''')