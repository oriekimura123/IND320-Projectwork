# /core/data_loader.py:
import pandas as pd
import os
from pyspark.sql import SparkSession 

# --- BEREGN ROTMAPPEN (Kun én mappe opp fra /core/) ---
# os.path.dirname(os.path.abspath(__file__)) gir stien til /core/
# Vi går én mappe opp fra /core/ for å få Rotmappen (IND320-PROJECTWORK-ORIE)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sett data-stien som en fast konstant
DATA_FOLDER = os.path.join(REPO_ROOT, 'data')

# -----------------------------------------------------------------

# def load_csv_with_pandas(filename: str) -> pd.DataFrame:
#    """
#    Laster en CSV-fil fra /data-mappen ved å bruke den ABSOLUTTE stien.
#    """
#    
#    # 1. Bygg den fullstendige, ABSOLUTTE stien: Rotmappe/data/filnavn
#    data_path = os.path.join(DATA_FOLDER, filename) 
#    # Laster dataen
#    df = pd.read_csv(data_path) 
#    
#    # Sjekk at denne blokken er der og er riktig:
#    if 'time' in df.columns:
#        df['time'] = pd.to_datetime(df['time'])
#        
#    return df

from .path_utils import get_absolute_path
import pandas as pd

def load_csv_with_pandas(filename: str):
    # Finner den sikre, ABSOLUTTE stien: Roten + 'data/open-meteo-subset.csv'
    absolute_file_path = get_absolute_path('data/' + filename)
    
    # Koden er nå immun mot hvor den kjøres fra!
    df = pd.read_csv(absolute_file_path)
 
    # Sjekk at denne blokken er der og er riktig:
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
 
    return df

def load_csv_with_spark(spark: SparkSession, filename: str): # <--- NY SIGNATUR
    """
    Laster en CSV-fil til en Spark DataFrame ved å bruke den ABSOLUTTE stien.
    Krever en SparkSession som argument.
    """
    
    # Bygg den ABSOLUTTE stien
    data_path = os.path.join(DATA_FOLDER, filename) 
    
    spark_df = spark.read.csv(
        data_path, 
        header=True, 
        inferSchema=True
    )
    
    return spark_df

