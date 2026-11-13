-- fact_inventory: transaction fact, grain 1 baris = 1 pergerakan stok.
select
    m.transaction_id,                                   -- degenerate dimension
    m.transfer_id,                                      -- degenerate dimension (khusus TRANSFER)
    m.transfer_direction,
    {{ date_key('m.transaction_date') }}  as date_key,
    p.product_key,
    w.warehouse_key,
    t.movement_type_key,
    m.transaction_timestamp,
    m.quantity,                                         -- additive, selalu positif
    cast(case
        when m.movement_type = 'TRANSFER' and m.transfer_direction = 'IN'  then  m.quantity
        when m.movement_type = 'TRANSFER' and m.transfer_direction = 'OUT' then -m.quantity
        else m.quantity * t.direction_sign
    end as bigint) as signed_quantity                   -- additive, + masuk / - keluar
from {{ ref('stg_inventory_movements') }} m
join {{ ref('dim_product') }}       p on m.product_id    = p.product_id
join {{ ref('dim_warehouse') }}     w on m.warehouse_id  = w.warehouse_id
join {{ ref('dim_movement_type') }} t on m.movement_type = t.movement_type
