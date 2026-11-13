-- BQ5: Inventory aging per kategori produk di setiap gudang.
select
    p.category,
    w.warehouse_name,
    round(cast(sum(s.stock_on_hand) as numeric)
          / nullif(sum(s.qty_out), 0), 1)                       as aging_days
from {{ ref('fact_inventory_daily_snapshot') }} s
join {{ ref('dim_product') }}   p on s.product_key = p.product_key
join {{ ref('dim_warehouse') }} w on s.warehouse_key = w.warehouse_key
group by p.category, w.warehouse_name
order by p.category, w.warehouse_name
