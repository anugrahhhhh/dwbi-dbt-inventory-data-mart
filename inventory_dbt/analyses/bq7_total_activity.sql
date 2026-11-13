-- BQ7: Total aktivitas (jumlah transaksi) untuk setiap jenis pergerakan.
select
    t.movement_type,
    t.movement_group,
    count(*)        as total_activity,
    sum(f.quantity) as total_units
from {{ ref('fact_inventory') }} f
join {{ ref('dim_movement_type') }} t on f.movement_type_key = t.movement_type_key
group by t.movement_type, t.movement_group
order by total_activity desc, t.movement_type  -- tie-breaker agar urutan stabil
