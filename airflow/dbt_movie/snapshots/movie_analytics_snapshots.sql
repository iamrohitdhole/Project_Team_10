{% snapshot movie_analytics_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='movie_id',
        strategy='check',
        check_cols=['MOVIE_TITLE', 'RELEASE_DATE', 'ORIGINAL_LANGUAGE', 'VOTE_COUNT', 'VOTE_AVERAGE', 'POPULARITY']
    )
}}

WITH deduplicated_movies AS (
    SELECT
        MOVIE_ID,
        MOVIE_TITLE,
        RELEASE_DATE,
        ORIGINAL_LANGUAGE,
        VOTE_COUNT,
        VOTE_AVERAGE,
        POPULARITY,
        ROW_NUMBER() OVER (PARTITION BY MOVIE_ID ORDER BY RELEASE_DATE DESC) AS rn
    FROM 
        {{ source('analytics', 'staging_imdb_tmdb_movies') }}
)
SELECT DISTINCT
    MOVIE_ID,
    MOVIE_TITLE,
    RELEASE_DATE,
    ORIGINAL_LANGUAGE,
    VOTE_COUNT,
    VOTE_AVERAGE,
    POPULARITY
FROM deduplicated_movies
WHERE rn = 1

{% endsnapshot %}