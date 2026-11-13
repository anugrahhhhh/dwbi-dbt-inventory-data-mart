-- dim_product (SCD Type 1): ambil hanya versi terbaru setiap product_id.
with ranked_products as (
    select
        product_id, product_name, category, brand, product_status, updated_at,
        row_number() over (
            partition by product_id              -- kelompokkan per natural key
            order by updated_at desc nulls last  -- versi terbaru di urutan 1
        ) as row_num
    from {{ ref('stg_products') }}
    where product_id is not null
)
select
    cast(row_number() over (order by product_id) as integer) as product_key,  -- surrogate key
    product_id, product_name, category, brand, product_status
from ranked_products
where row_num = 1
