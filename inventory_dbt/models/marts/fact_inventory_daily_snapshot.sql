-- fact_inventory_daily_snapshot: periodic snapshot fact (fact-on-fact).
-- Grain: 1 baris = 1 produk x 1 gudang x 1 hari, termasuk hari tanpa transaksi.
with harian as (                       -- ringkas fakta transaksi per hari
    select
        date_key, product_key, warehouse_key,
        sum(case when signed_quantity > 0 then  signed_quantity else 0 end) as qty_in,
        sum(case when signed_quantity < 0 then -signed_quantity else 0 end) as qty_out
    from {{ ref('fact_inventory') }}
    group by date_key, product_key, warehouse_key
),
kerangka as (                          -- semua kombinasi produk x gudang x tanggal
    select d.date_key, p.product_key, w.warehouse_key
    from {{ ref('dim_date') }} d
    cross join {{ ref('dim_product') }} p
    cross join {{ ref('dim_warehouse') }} w
)
select
    k.date_key,
    k.product_key,
    k.warehouse_key,
    cast(coalesce(h.qty_in, 0)  as bigint)                    as qty_in,       -- additive
    cast(coalesce(h.qty_out, 0) as bigint)                    as qty_out,      -- additive
    cast(coalesce(h.qty_in, 0) - coalesce(h.qty_out, 0) as bigint) as net_change,
    cast(sum(coalesce(h.qty_in, 0) - coalesce(h.qty_out, 0)) over (
        partition by k.product_key, k.warehouse_key
        order by k.date_key
        rows between unbounded preceding and current row
    ) as bigint)                                              as stock_on_hand -- semi-additive
from kerangka k
left join harian h
  on  h.date_key = k.date_key
  and h.product_key = k.product_key
  and h.warehouse_key = k.warehouse_key
