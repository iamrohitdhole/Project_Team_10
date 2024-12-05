WITH movies_data AS (
    SELECT *
    FROM {{ ref('staging_imdb_tmdb_movies') }}
)

SELECT
    movie_id,
    movie_title,
    release_date,
    popularity
FROM movies_data
ORDER BY popularity DESC
LIMIT 10