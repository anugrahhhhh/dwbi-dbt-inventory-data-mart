-- BQ3: Peta aktivitas: jumlah transaksi tiap jenis pergerakan di setiap gudang (bentuk matriks).
select
    w.warehouse_name,
    sum(case when t.movement_type = 'SALE'     then 1 else 0 end) as "SALE",
    sum(case when t.movement_type = 'PURCHASE' then 1 else 0 end) as "PURCHASE",
    sum(case when t.movement_type = 'TRANSFER' then 1 else 0 end) as "TRANSFER",
    sum(case when t.movement_type = 'LOST'     then 1 else 0 end) as "LOST",
    sum(case when t.movement_type = 'DAMAGED'  then 1 else 0 end) as "DAMAGED",
    sum(case when t.movement_type = 'FOUND'    then 1 else 0 end) as "FOUND"
from {{ ref('fact_inventory') }} f
join {{ ref('dim_warehouse') }}     w on f.warehouse_key = w.warehouse_key
join {{ ref('dim_movement_type') }} t on f.movement_type_key = t.movement_type_key
group by w.warehouse_name
order by w.warehouse_name
