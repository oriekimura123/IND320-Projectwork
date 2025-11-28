# streamlit_app/utils/database_interaction.py
# 

import streamlit as st

# Set up sparksession
from pyspark.sql import SparkSession

def setup_spark_session(app_name: str) -> SparkSession:
    spark = (
        SparkSession.builder
        .appName(app_name)
        # Cassandra config
        .config("spark.cassandra.connection.host", "localhost")
        # .config("spark.cassandra.connection.host", "host.docker.internal")
        .config("spark.cassandra.connection.port", "9042")
        .config('spark.sql.extensions', 'com.datastax.spark.connector.CassandraSparkExtensions')
        .config('spark.sql.catalog.mycatalog', 'com.datastax.spark.connector.datasource.CassandraCatalog')
        .config("spark.jars.packages", "com.datastax.spark:spark-cassandra-connector_2.12:3.5.1")
        .config("spark.cassandra.connection.timeout_ms", "60000")
        .getOrCreate()
    )

    # Spark config
    spark_master = spark.sparkContext.master
    spark_conf = spark.sparkContext.getConf().getAll()

    return spark


# Set up Cassandra connection and create keyspace
# IMPORTANT: Ensure your Docker container is running and wait ~90 seconds 
# before running this cell to allow Cassandra to fully start.

from cassandra.cluster import Session
from cassandra.cluster import ConnectionException, OperationTimedOut

def create_cassandra_keyspace_and_table(
    session: Session, 
    keyspace_name: str, 
    table_name: str
):
    """
    Creates the Cassandra keyspace and the specified table. 
    Handles connection errors and separates the creation logic.
    """
    # --- DROP TABLE (If you need a clean start) ---
    try:
        drop_query = f"DROP TABLE IF EXISTS {keyspace_name}.{table_name};"
        session.execute(drop_query)
        print(f"--Table '{keyspace_name}.{table_name}' dropped (if it existed).")
        
    except ConnectionException:
        print(f" ERROR: Cannot connect to Cassandra to drop table. Exiting.")
        return # Stop execution if connection fails
    except Exception as e:
        # Catch other potential errors, like network issues or timeouts
        print(f" ERROR: Unexpected error while dropping table: {e}")
        # You may choose to continue here if dropping isn't strictly necessary

    # --- 1. KEYSAPCE CREATION ---
    try:
        keyspace_query = f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace_name} 
            WITH REPLICATION = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """
        session.execute(keyspace_query)
        print(f"--Keyspace '{keyspace_name}' confirmed/created.")
        
    except ConnectionException:
        print(f"ERROR: Failed to connect to Cassandra. Check the cluster status.")
        return # Stop execution if connection fails
    except Exception as e:
        print(f"ERROR: Unexpected error during Keyspace creation: {e}")
        return

    # --- 2. SET KEYSPACE AND DROP/CREATE TABLE ---
    try:
        # Set the keyspace for subsequent operations
        session.set_keyspace(keyspace_name)
        print(f"--Session set to keyspace '{keyspace_name}'.")

        # Define the table schema using proper indentation and formatting
        table_schema = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ind bigint PRIMARY KEY,
                pricearea text, 
                datatype text, 
                groupname text, 
                starttime text,
                endtime text,
                lastupdatedtime text,
                quantitykwh double 
            );
        """
        session.execute(table_schema)
        print(f"---Table '{table_name}' confirmed/created.")
        
    except OperationTimedOut:
        print(f"ERROR: Cassandra operation timed out.")
    except Exception as e:
        print(f"ERROR: Failed to create table '{table_name}'. Error: {e}")


# Write to Cassandra
def write_to_cassandra(df_spark, keyspace: str, table_name: str):
    """Writes the Spark DataFrame to Cassandra."""
    df_spark \
        .format("org.apache.spark.sql.cassandra") \
        .options(table=table_name, keyspace=keyspace) \
        .mode("append") \
        .save()
    