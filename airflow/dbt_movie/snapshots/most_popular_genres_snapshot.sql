{% snapshot most_popular_genres_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='genre_name',
        strategy='check',
        check_cols=['movie_count', 'avg_popularity']
    )
}}

SELECT
    genre_name,
    movie_count,
    avg_popularity
FROM 
    {{ ref('most_popular_genres') }}

{% endsnapshot %}