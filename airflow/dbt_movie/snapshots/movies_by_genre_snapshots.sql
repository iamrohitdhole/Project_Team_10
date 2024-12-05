{% snapshot movies_by_genre_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='genre',
        strategy='check',
        check_cols=['movie_count']
    )
}}

SELECT
    genre,
    movie_count
FROM 
    {{ ref('movies_by_genre') }}

{% endsnapshot %}