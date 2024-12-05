from airflow import DAG
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.utils.dates import days_ago
import requests
import gzip
import pandas as pd
from datetime import datetime

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

imdb_dag = DAG(
    'etl_imdb_current_year',
    default_args=default_args,
    description='Load IMDb current year movie data into Snowflake',
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
)

@task
def fetch_imdb_data(dataset_url: str):
    response = requests.get(dataset_url, stream=True)
    if response.status_code == 200:
        file_path = '/tmp/imdb_dataset.tsv.gz'
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Extracted IMDb dataset to {file_path}")
        return file_path
    else:
        raise Exception(f"Failed to download IMDb dataset. HTTP Status: {response.status_code}")

@task
def transform_imdb_data(file_path: str):
    with gzip.open(file_path, 'rt') as f:
        df = pd.read_csv(f, sep='\t', low_memory=False)

    # Get the current year
    current_year = datetime.now().year

    # Ensure 'startYear' is numeric and filter for the current year
    df['startYear'] = pd.to_numeric(df['startYear'], errors='coerce')
    df = df[(df['titleType'] == 'movie') & (df['startYear'] == current_year)]
    df = df.dropna(subset=['tconst', 'primaryTitle', 'startYear', 'genres'])

    # Select key columns and deduplicate
    df = df[['tconst', 'titleType', 'primaryTitle', 'startYear', 'genres']]
    df = df.drop_duplicates(subset=['tconst'])

    print(f"Transformed {len(df)} movie records for the current year ({current_year}).")
    return df.to_dict(orient='records')

@task
def load_imdb_data_to_snowflake(records: list):
    if not records:
        print("No records to load into Snowflake.")
        return

    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')
    conn = hook.get_conn()
    cur = conn.cursor()

    target_table = "movies.raw_data.imdb_data_movies"

    try:
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_table} (
            tconst VARCHAR PRIMARY KEY,
            titleType VARCHAR,
            primaryTitle VARCHAR,
            startYear INTEGER,
            genres VARCHAR
        )
        """)

        for r in records:
            sql = f"""
            MERGE INTO {target_table} AS target
            USING (SELECT '{r['tconst']}' AS tconst, 
                          '{r['titleType']}' AS titleType, 
                          '{r['primaryTitle'].replace("'", "''")}' AS primaryTitle, 
                          {r['startYear']} AS startYear, 
                          '{r['genres'].replace("'", "''")}' AS genres) AS source
            ON target.tconst = source.tconst
            WHEN MATCHED THEN UPDATE 
                SET titleType = source.titleType,
                    primaryTitle = source.primaryTitle,
                    startYear = source.startYear,
                    genres = source.genres
            WHEN NOT MATCHED THEN INSERT 
                (tconst, titleType, primaryTitle, startYear, genres)
                VALUES (source.tconst, source.titleType, source.primaryTitle, source.startYear, source.genres)
            """
            cur.execute(sql)

        conn.commit()
        print(f"Successfully loaded {len(records)} records into Snowflake table: {target_table}.")
    except Exception as e:
        conn.rollback()
        print(f"Error loading IMDb data: {e}")
    finally:
        cur.close()
        conn.close()

with imdb_dag:
    # Task flow
    file_path = fetch_imdb_data("https://datasets.imdbws.com/title.basics.tsv.gz")
    transformed_data = transform_imdb_data(file_path)
    load_imdb_data_to_snowflake(transformed_data)
