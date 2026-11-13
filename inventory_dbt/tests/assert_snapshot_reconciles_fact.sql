-- Rekonsiliasi antarfakta: stok pada hari terakhir = total signed_quantity seluruh transaksi.
with dari_fakta as (
    select product_key, warehouse_key, sum(signed_quantity) as stok_fakta
    from {{ ref('fact_inventory') }}
    group by product_key, warehouse_key
),
dari_snapshot as (
    select product_key, warehouse_key, stock_on_hand as stok_snapshot
    from {{ ref('fact_inventory_daily_snapshot') }}
    where date_key = {{ var('end_date') | replace('-', '') }}
)
select s.product_key, s.warehouse_key, s.stok_snapshot, coalesce(f.stok_fakta, 0) as stok_fakta
from dari_snapshot s
left join dari_fakta f
  on s.product_key = f.product_key and s.warehouse_key = f.warehouse_key
where s.stok_snapshot <> coalesce(f.stok_fakta, 0)
