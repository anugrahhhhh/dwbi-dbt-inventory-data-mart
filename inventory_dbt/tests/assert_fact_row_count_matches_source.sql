-- Kelengkapan: tidak ada baris pergerakan yang hilang saat join ke dimensi.
select sumber, fakta from (
    select (select count(*) from {{ source('inventory_oltp', 'source_inventory_movements') }}) as sumber,
           (select count(*) from {{ ref('fact_inventory') }}) as fakta
) x
where sumber <> fakta
