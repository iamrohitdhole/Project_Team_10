WITH split_genres AS (
    SELECT
        movie_id,
        SPLIT(genres, ',') AS genre_array,
        vote_count
    FROM {{ ref('staging_imdb_tmdb_movies') }}
),
flattened_genres AS (
    SELECT
        movie_id,
        genre.VALUE AS genre,
        vote_count
    FROM split_genres, TABLE(FLATTEN(INPUT => genre_array)) AS genre
)
SELECT
    genre,
    AVG(vote_count) AS avg_vote_count
FROM flattened_genres
GROUP BY genre