-- Staging pergerakan stok: seragamkan huruf, tipe data quantity BIGINT, tanggal transaksi.
select
    trim(transaction_id)                         as transaction_id,
    nullif(trim(transfer_id), '')                as transfer_id,
    upper(nullif(trim(transfer_direction), ''))  as transfer_direction,
    trim(product_id)                             as product_id,
    trim(warehouse_id)                           as warehouse_id,
    upper(trim(movement_type))                   as movement_type,
    cast(quantity as bigint)                     as quantity,
    cast(transaction_timestamp as timestamp)     as transaction_timestamp,
    cast(transaction_timestamp as date)          as transaction_date
from {{ source('inventory_oltp', 'source_inventory_movements') }}
