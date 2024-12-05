{% snapshot top_10_most_popular_movies_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='movie_id',
        strategy='check',
        check_cols=['popularity']
    )
}}

SELECT
    movie_id,
    movie_title,
    release_date,
    popularity
FROM 
    {{ ref('top_10_most_popular_movies') }}

{% endsnapshot %}