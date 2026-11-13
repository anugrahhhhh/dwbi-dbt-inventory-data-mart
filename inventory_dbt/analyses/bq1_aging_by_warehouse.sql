-- BQ1: Berapa hari rata-rata stok tertahan di setiap gudang (inventory aging)?
-- aging_days = total stok harian / total unit keluar  (memakai periodic snapshot)
select
    w.warehouse_name,
    sum(s.stock_on_hand)                                        as total_stock_days,
    sum(s.qty_out)                                              as total_qty_out,
    round(cast(sum(s.stock_on_hand) as numeric)
          / nullif(sum(s.qty_out), 0), 1)                       as aging_days
from {{ ref('fact_inventory_daily_snapshot') }} s
join {{ ref('dim_warehouse') }} w on s.warehouse_key = w.warehouse_key
group by w.warehouse_name
order by aging_days
