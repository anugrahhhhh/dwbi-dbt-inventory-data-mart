-- Staging produk: rapikan teks (TRIM), string kosong -> NULL (NULLIF). Tanpa logika bisnis.
select
    nullif(trim(product_id), '')      as product_id,
    nullif(trim(product_name), '')    as product_name,
    nullif(trim(category), '')        as category,
    nullif(trim(brand), '')           as brand,
    nullif(trim(product_status), '')  as product_status,
    cast(updated_at as timestamp)     as updated_at
from {{ source('inventory_oltp', 'source_products') }}
