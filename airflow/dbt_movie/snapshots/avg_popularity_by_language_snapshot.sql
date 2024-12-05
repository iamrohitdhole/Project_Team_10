{% snapshot avg_popularity_by_language_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='original_language',
        strategy='check',
        check_cols=['avg_popularity', 'movie_count']
    )
}}

SELECT
    original_language,
    avg_popularity,
    movie_count
FROM 
    {{ ref('avg_popularity_by_language') }}

{% endsnapshot %}