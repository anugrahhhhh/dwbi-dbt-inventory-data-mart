-- BQ4: Jumlah aktivitas per gudang dan jenis pergerakan (bentuk panjang, untuk grouped bar).
select
    w.warehouse_name,
    t.movement_type,
    count(*) as total_activity
from {{ ref('fact_inventory') }} f
join {{ ref('dim_warehouse') }}     w on f.warehouse_key = w.warehouse_key
join {{ ref('dim_movement_type') }} t on f.movement_type_key = t.movement_type_key
group by w.warehouse_name, t.movement_type
order by w.warehouse_name, t.movement_type
