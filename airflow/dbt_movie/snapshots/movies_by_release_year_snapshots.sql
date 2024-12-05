{% snapshot movies_by_release_year_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='release_year',
        strategy='check',
        check_cols=['total_movies', 'avg_popularity']
    )
}}

SELECT
    release_year,
    total_movies,
    avg_popularity
FROM 
    {{ ref('movies_by_release_year') }}

{% endsnapshot %}