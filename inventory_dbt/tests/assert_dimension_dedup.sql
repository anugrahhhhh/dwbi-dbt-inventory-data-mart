-- Dedup dimensi: jumlah baris dimensi harus sama dengan jumlah ID unik di sumber.
-- PASS bila kueri menghasilkan 0 baris.
with cek as (
    select 'dim_product' as dimensi,
           (select count(*) from {{ ref('dim_product') }}) as baris_dimensi,
           (select count(distinct product_id) from {{ ref('stg_products') }}) as id_unik_sumber
    union all
    select 'dim_warehouse',
           (select count(*) from {{ ref('dim_warehouse') }}),
           (select count(distinct warehouse_id) from {{ ref('stg_warehouses') }})
)
select * from cek where baris_dimensi <> id_unik_sumber
