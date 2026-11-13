-- BQ6: Berapa unit hilang (LOST) dan rusak (DAMAGED) per kategori produk di setiap gudang?
select
    p.category,
    w.warehouse_name,
    sum(case when t.movement_type = 'LOST'    then f.quantity else 0 end) as units_lost,
    sum(case when t.movement_type = 'DAMAGED' then f.quantity else 0 end) as units_damaged,
    sum(f.quantity)                                                       as units_lost_damaged
from {{ ref('fact_inventory') }} f
join {{ ref('dim_product') }}       p on f.product_key = p.product_key
join {{ ref('dim_warehouse') }}     w on f.warehouse_key = w.warehouse_key
join {{ ref('dim_movement_type') }} t on f.movement_type_key = t.movement_type_key
where t.movement_type in ('LOST', 'DAMAGED')
group by p.category, w.warehouse_name
order by p.category, w.warehouse_name
