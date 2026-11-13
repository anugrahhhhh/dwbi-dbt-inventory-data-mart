-- dim_warehouse (SCD Type 1): ambil hanya versi terbaru setiap warehouse_id.
with ranked_warehouses as (
    select
        warehouse_id, warehouse_name, city, region, warehouse_type, updated_at,
        row_number() over (
            partition by warehouse_id
            order by updated_at desc nulls last
        ) as row_num
    from {{ ref('stg_warehouses') }}
    where warehouse_id is not null
)
select
    cast(row_number() over (order by warehouse_id) as integer) as warehouse_key,
    warehouse_id, warehouse_name, city, region, warehouse_type
from ranked_warehouses
where row_num = 1
