-- Staging gudang: rapikan teks dan ubah string kosong menjadi NULL.
select
    nullif(trim(warehouse_id), '')    as warehouse_id,
    nullif(trim(warehouse_name), '')  as warehouse_name,
    nullif(trim(city), '')            as city,
    nullif(trim(region), '')          as region,
    nullif(trim(warehouse_type), '')  as warehouse_type,
    cast(updated_at as timestamp)     as updated_at
from {{ source('inventory_oltp', 'source_warehouses') }}
