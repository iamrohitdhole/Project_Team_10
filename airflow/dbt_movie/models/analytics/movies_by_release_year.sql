-- models/analytics/movies_by_release_year.sql

WITH year_data AS (
    SELECT
        EXTRACT(YEAR FROM release_date) AS release_year,
        COUNT(*) AS total_movies,
        AVG(popularity) AS avg_popularity
    FROM {{ ref('staging_imdb_tmdb_movies') }}
    GROUP BY release_year
)

SELECT
    release_year,
    total_movies,
    avg_popularity
FROM year_data
ORDER BY release_year DESC