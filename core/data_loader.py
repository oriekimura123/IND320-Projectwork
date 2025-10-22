# /core/data_loader.py:
import pandas as pd
import os
from pyspark.sql import SparkSession 

# Calculate the root folder (Only one folder up from /core/)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set the data path as a fixed constant
DATA_FOLDER = os.path.join(REPO_ROOT, 'data')

from .path_utils import get_absolute_path
import pandas as pd

def load_csv_with_pandas(filename: str):
    # Loads a CSV file into a dataframe pandas using the ABSOLUTE path.
    # Finds the safe, ABSOLUTE path: Root +
    absolute_file_path = get_absolute_path('data/' + filename)
    
    # Read the csv file
    df = pd.read_csv(absolute_file_path)
 
    # Check that this block is there and correct:
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
 
    return df

def load_csv_with_spark(spark: SparkSession, filename: str): 
    # Loads a CSV file into a Spark DataFrame using the ABSOLUTE path.
    # Requires a SparkSession as an argument.
    
    # Finds the safe, ABSOLUTE path: Root +
    data_path = os.path.join(DATA_FOLDER, filename) 
    
    # Read the csv file
    spark_df = spark.read.csv(
        data_path, 
        header=True, 
        inferSchema=True
    )
    
    return spark_df

