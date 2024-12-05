from airflow import DAG
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.models import Variable
from airflow.utils.dates import days_ago
import requests
from datetime import datetime, timedelta

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

# Initialize the ETL DAG
tmdb_dag = DAG(
    'etl_tmdb_movies',
    default_args=default_args,
    description='ETL process for fetching TMDb movies released strictly in the last 7 days',
    schedule_interval='0 0 * * 0',  # Run every Sunday at midnight
    start_date=days_ago(1),
    catchup=False,
)

# Task 1: Fetch the last processed date from Airflow variable or Snowflake
@task
def get_last_processed_date():
    try:
        # Attempt to get the last processed date from Airflow Variable or metadata table
        last_processed_date = Variable.get("last_processed_date", default_var=None)  # Default is None if not set
        print(f"Last processed date from Variable: {last_processed_date}")
    except Exception as e:
        last_processed_date = None
        print(f"Could not fetch last processed date: {e}")
    return last_processed_date

# Task 2: Fetch movies released strictly in the past 7 days
@task
def extract_tmdb_movies_last_seven_days():
    api_key = Variable.get("tmdb_api_key")  # Fetch API key from Airflow Variables
    # Fetch movies released in the last 7 days (strictly)
    date_seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    today_date = datetime.now().strftime('%Y-%m-%d')

    url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&region=US&primary_release_date.gte={date_seven_days_ago}&primary_release_date.lte={today_date}"

    all_movies = []
    page = 1
    while True:
        response = requests.get(f"{url}&page={page}")
        
        if response.status_code == 200:
            data = response.json()
            movies = data.get('results', [])
            all_movies.extend(movies)
            
            # If there are no more pages, break the loop
            if page >= data['total_pages']:
                break
            page += 1
        else:
            raise Exception(f"Failed to fetch TMDb data. HTTP Status: {response.status_code}")
    
    print(f"Extracted {len(all_movies)} movies released in the last 7 days.")
    return all_movies

import random

@task
def transform_tmdb_data(data: list):
    """
    Transform TMDb data to include required fields, replacing missing or zero values with random integer values.
    Also maps genre_ids to genre names using a predefined genre mapping.
    """
    if not data:
        print("No data provided for transformation.")
        return []

    # Genre mapping (this can also be fetched dynamically if needed)
    genre_mapping = {
        28: "Action",
        12: "Adventure",
        16: "Animation",
        35: "Comedy",
        80: "Crime",
        99: "Documentary",
        18: "Drama",
        10751: "Family",
        14: "Fantasy",
        36: "History",
        27: "Horror",
        10402: "Music",
        9648: "Mystery",
        10749: "Romance",
        878: "Science Fiction",
        10770: "TV Movie",
        53: "Thriller",
        10752: "War",
        37: "Western"
    }

    # Filter movies released in the last week
    one_week_ago = datetime.now() - timedelta(days=7)
    valid_movies = [
        movie for movie in data if movie.get("release_date") and datetime.strptime(movie["release_date"], "%Y-%m-%d") >= one_week_ago
    ]

    # Function to generate random values within a range
    def generate_random_value(field_type: str):
        if field_type == "popularity":
            return random.randint(1, 10)  # Random integer between 1 and 10 for popularity
        elif field_type == "vote_average":
            return random.randint(1, 10)  # Random integer between 1 and 10 for vote average
        elif field_type == "vote_count":
            return random.randint(1, 20)  # Random integer between 1 and 20 for vote count
        return 0  # Default case for other fields

    # Transform data and replace missing or zero values with random values, and map genre ids to genre names
    transformed = []
    for movie in valid_movies:
        transformed_movie = {
            "movie_id": movie.get("id"),
            "title": movie.get("title"),
            "release_date": movie.get("release_date"),
            "original_language": movie.get("original_language"),
            "popularity": movie.get("popularity") if movie.get("popularity") and movie.get("popularity") > 0 else generate_random_value("popularity"),
            "vote_average": movie.get("vote_average") if movie.get("vote_average") and movie.get("vote_average") > 0 else generate_random_value("vote_average"),
            "vote_count": movie.get("vote_count") if movie.get("vote_count") and movie.get("vote_count") > 0 else generate_random_value("vote_count"),
            "genre_ids": ",".join([genre_mapping.get(genre_id, str(genre_id)) for genre_id in movie.get("genre_ids", [])]),
        }
        transformed.append(transformed_movie)

    print(f"Transformed {len(transformed)} movies from the last week with missing or zero values replaced by random integer values and genres mapped.")
    return transformed



# Task 4: Load TMDb data into Snowflake incrementally
@task
def load_tmdb_data_to_snowflake(records: list):
    if not records:
        print("No records to load into Snowflake.")
        return

    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')
    conn = hook.get_conn()
    cur = conn.cursor()

    target_table = "movies.raw_data.tmdb_data_movies"

    try:
        print("Starting transaction...")

        # Begin the SQL transaction explicitly
        cur.execute("BEGIN;")

        # Create table if it doesn't exist
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {target_table} (
            movie_id INTEGER PRIMARY KEY,
            title VARCHAR,
            release_date DATE,
            original_language VARCHAR,
            popularity FLOAT,
            vote_average FLOAT,
            vote_count INTEGER,
            genre_ids TEXT
        )
        """)

        # Load data with a MERGE statement (for incremental updates)
        for r in records:
            sql = f"""
            MERGE INTO {target_table} AS target
            USING (SELECT {r['movie_id']} AS movie_id, 
                          '{r['title'].replace("'", "''")}' AS title, 
                          TO_DATE('{r['release_date']}', 'YYYY-MM-DD') AS release_date, 
                          '{r['original_language']}' AS original_language, 
                          {r['popularity']} AS popularity, 
                          {r['vote_average']} AS vote_average, 
                          {r['vote_count']} AS vote_count, 
                          '{r['genre_ids']}' AS genre_ids) AS source
            ON target.movie_id = source.movie_id
            WHEN MATCHED THEN UPDATE 
                SET title = source.title,
                    release_date = source.release_date,
                    original_language = source.original_language,
                    popularity = source.popularity,
                    vote_average = source.vote_average,
                    vote_count = source.vote_count,
                    genre_ids = source.genre_ids
            WHEN NOT MATCHED THEN INSERT 
                (movie_id, title, release_date, original_language, popularity, vote_average, vote_count, genre_ids)
                VALUES (source.movie_id, source.title, source.release_date, source.original_language, source.popularity, source.vote_average, source.vote_count, source.genre_ids)
            """
            cur.execute(sql)

        # Commit the transaction after all operations
        conn.commit()
        print(f"Successfully loaded {len(records)} records into Snowflake table: {target_table}.")

        # Update the last processed date to the latest movie's release date
        latest_release_date = max([datetime.strptime(r['release_date'], "%Y-%m-%d") for r in records])
        Variable.set("last_processed_date", latest_release_date.strftime("%Y-%m-%d"))
        print(f"Last processed date updated to: {latest_release_date.strftime('%Y-%m-%d')}")

    except Exception as e:
        conn.rollback()
        print(f"Error during loading data: {e}")
    finally:
        cur.close()
        conn.close()


# Define task dependencies
with tmdb_dag:
    new_tmdb_movies = extract_tmdb_movies_last_seven_days()
    transformed_movies = transform_tmdb_data(new_tmdb_movies)
    load_tmdb_data_to_snowflake(transformed_movies)
