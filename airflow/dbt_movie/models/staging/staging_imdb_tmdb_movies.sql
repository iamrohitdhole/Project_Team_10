-- models/staging/staging_imdb_tmdb_movies.sql

WITH imdb_data AS (
    SELECT
        primaryTitle AS title,
        genres
    FROM {{ source('raw_data','imdb_data_movies') }}  -- Referring to the IMDb raw data model
),

tmdb_data AS (
    SELECT
        movie_id,
        title,
        release_date,
        original_language,
        vote_count,
        vote_average,
        popularity  -- Including popularity field
    FROM {{ source('raw_data','tmdb_data_movies') }}  -- Referring to the TMDb raw data model
)

SELECT
    imdb.title AS primary_title,
    imdb.genres,
    tmdb.movie_id,
    tmdb.title AS movie_title,
    tmdb.release_date,
    tmdb.original_language,
    tmdb.vote_count,
    tmdb.vote_average,
    tmdb.popularity  
FROM tmdb_data tmdb
LEFT JOIN imdb_data imdb
    ON tmdb.title = imdb.title