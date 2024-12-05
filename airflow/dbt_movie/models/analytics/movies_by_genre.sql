WITH split_genres AS (
    SELECT
        movie_id,
        SPLIT(genres, ',') AS genre_array
    FROM {{ ref('staging_imdb_tmdb_movies') }}
),
flattened_genres AS (
    SELECT
        movie_id,
        genre.VALUE AS genre
    FROM split_genres, TABLE(FLATTEN(INPUT => genre_array)) AS genre
)
SELECT
    genre,
    COUNT(movie_id) AS movie_count
FROM flattened_genres
GROUP BY genre