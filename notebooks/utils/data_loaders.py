# streamlit_app/utils/data_loaders.py
import os
import pandas as pd
import streamlit as st
from pymongo import MongoClient
import requests
from typing import Optional, Dict, Any
from typing import List, Dict
from datetime import date, time
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import quote

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# @st.cache_data(show_spinner=True)
def fetch_elhub_data(
    start_date: date,
    end_date: date,
    dataset_type: str, # e.g., DATASET_PRODUCTION or DATASET_CONSUMPTION
    price_areas: List[str],
    base_url:str,
    max_retries: int,
    delay_seconds: float
) -> List[Dict]:
    """Fetches hourly data for a given range and dataset type from Elhub API."""
    
    # --- Main Data Storage ---
    all_data: List[Dict] = []
    total_records_collected = 0

    # 1. LOOP THROUGH YEARS/MONTHS/AREAS (similar logic to your existing script)
    for area in price_areas:
        current_start_date = start_date

        while current_start_date <= end_date:
            next_month_start = current_start_date + relativedelta(months=1)
            current_end_date = next_month_start - relativedelta(days=1)

            if current_end_date > end_date:
                current_end_date = end_date

            # Define timezone (+01:00 for Norway, UTC+1)
            TZ_OFFSET = timezone(timedelta(hours=1))

            # Convert date (which has no time) to datetime with timezone
            start_dt = datetime.combine(current_start_date, datetime.min.time(), tzinfo=TZ_OFFSET)
            end_dt = datetime.combine(current_end_date + timedelta(days=1), datetime.min.time(), tzinfo=TZ_OFFSET)

            # Create proper ISO-8601 timestamps and encode them
            start_date_str = quote(start_dt.isoformat(), safe="")
            end_date_str = quote(end_dt.isoformat(), safe="")

            # Construct URL using the parameterized dataset_type
            url = (
                f"{base_url}/{area}?{dataset_type}"
                f"&startDate={start_date_str}&endDate={end_date_str}"
            )
            # print(f"Fetching data from :{url}")
            # --- Retry Logic ---
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        print(f"   (Attempt {attempt + 1}/{max_retries}) Retrying in {delay_seconds}s...")
                        time.sleep(delay_seconds)
                    
                    # Make the API request
                    # response = requests.get(url, verify=False)
                    response = requests.get(url)
                    response.raise_for_status() 

                    # Extract and process data
                    data = response.json().get('data', [])
                    # Extract and Flatten Data
                    # If using Consumption, the inner key will change!
                    inner_key = 'consumptionPerGroupMbaHour' if 'CONSUMPTION' in dataset_type else 'productionPerGroupMbaHour'

                    for record in response.json().get('data', []):
                        record['priceArea'] = area 
                        attributes = record.get('attributes', {})
                        data_list = attributes.get(inner_key, [])
                        
                        # Append the records to a single list (Production and Consumption have the same schema)
                        new_records_count = 0    
                        for item in data_list:
                            production_group = item.get('productionGroup')
                            consumption_group = item.get('consumptionGroup')
                            
                            if production_group:
                                    data_type = 'Production'
                                    group_name = production_group
                            elif consumption_group:
                                data_type = 'Consumption'
                                group_name = consumption_group
                            else:
                                # Fallback if neither is present (shouldn't happen based on your JSON)
                                data_type = 'Unknown'
                                group_name = None
                            
                            all_data.append({
                                # use to lowerecase keys to be Cassandra friendly
                                'pricearea': area,
                                'datatype': data_type,
                                'groupname': group_name,
                                'starttime': item['startTime'],
                                'endtime': item['endTime'],
                                'lastupdatedtime': item['lastUpdatedTime'],
                                'quantitykwh': item['quantityKwh']
                            })
                            new_records_count += 1
                    
                    # print(f"<- Successfully retrieved {len(data)} records for {area}.")
                    break # Success, move to the next month

                except requests.exceptions.HTTPError as errh:
                    print(f"HTTP Error for {area} ({start_date_str}): {errh}")
                    if response.status_code < 500 or attempt == max_retries - 1:
                        break # Stop retrying on client errors (4xx) or max attempts
                except requests.exceptions.RequestException as err:
                    print(f"General Request Error for {area} ({start_date_str}): {err}")
                    if attempt == max_retries - 1:
                        break

            # ... [Continue to next month] ...
            current_start_date = next_month_start            

    return all_data

@st.cache_data(show_spinner=True)
def load_mongoDB(collection_name: str, database_name: str) -> pd.DataFrame:
    """
    load data from remote MongoDB.

    Args:
        collection_name: str
        database_name: str

    Returns:
        pd.DataFrame which contains data collection_name:.database_name
    """
    mongo_uri = st.secrets["mongo"]["uri"]
    client = MongoClient(mongo_uri)
    db = client[database_name]
    df = pd.DataFrame(list(db[collection_name].find()))
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)
    return df
