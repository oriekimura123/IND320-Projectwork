# streamlit_app/utils/database_interaction.py
# 
# --- Required imports (pyspark, MongoClient, cassandra.cluster, etc.) ---
from cassandra.cluster import Cluster
from cassandra.cluster import ConnectionException
import streamlit as st
from pyspark.sql import SparkSession


def setup_spark_session(app_name: str) -> SparkSession:
    spark = (
        SparkSession.builder
        .appName(app_name)
        # Cassandra config
        .config("spark.cassandra.connection.host", "localhost")
        .config("spark.cassandra.connection.port", "9042")
        .config('spark.sql.extensions', 'com.datastax.spark.connector.CassandraSparkExtensions')
        .config('spark.sql.catalog.mycatalog', 'com.datastax.spark.connector.datasource.CassandraCatalog')
        .config("spark.jars.packages", "com.datastax.spark:spark-cassandra-connector_2.12:3.5.1")
        .getOrCreate()
    )

    # Spark config
    spark_master = spark.sparkContext.master
    spark_conf = spark.sparkContext.getConf().getAll()

    return spark

def create_cassandra_keyspace_and_table(session, keyspace: str, table_name: str):
    # ... [Your existing Cassandra keyspace and table creation logic] ...
    # Ensure the CREATE TABLE query includes all necessary columns (e.g., consumptionGroup)
    session.set_keyspace(keyspace)
    # New schema with consumptionGroup
    session.execute(f"CREATE TABLE IF NOT EXISTS {keyspace}.{table_name}(ind bigint primary key, \
        priceArea text, productiongroup text, consumptionGroup text, startTime text, endTime text, quantityKwh double, lastUpdatedTime text);")


def write_to_cassandra(df_spark, keyspace: str, table_name: str):
    """Writes the Spark DataFrame to Cassandra."""
    df_spark.write \
        .format("org.apache.spark.sql.cassandra") \
        .options(table=table_name, keyspace=keyspace) \
        .mode("append") \
        .save()
    
# NEW: Function to write directly to MongoDB (optional, but cleaner than Spark Mongo connector)
def write_to_mongodb(data_list: List[Dict], collection_name: str):
    """Writes the list of dicts directly to MongoDB."""
    # Connect to MongoDB and insert_many()
    # You will need to handle the MONGO_URI from st.secrets here.
    pass 
```

-----
