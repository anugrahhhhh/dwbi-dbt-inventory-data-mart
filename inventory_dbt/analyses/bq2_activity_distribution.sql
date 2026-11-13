-- BQ2: Bagaimana distribusi (proporsi) aktivitas inventory per jenis pergerakan?
select
    t.movement_type,
    count(*)                                                    as total_activity,
    round(cast(100.0 * count(*) / sum(count(*)) over () as numeric), 2) as pct
from {{ ref('fact_inventory') }} f
join {{ ref('dim_movement_type') }} t on f.movement_type_key = t.movement_type_key
group by t.movement_type
order by total_activity desc
