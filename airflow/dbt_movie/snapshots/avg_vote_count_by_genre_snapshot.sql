{% snapshot avg_vote_count_by_genre_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='genre',
        strategy='check',
        check_cols=['avg_vote_count']
    )
}}

SELECT
    genre,
    avg_vote_count
FROM 
    {{ ref('avg_vote_count_by_genre') }}

{% endsnapshot %}