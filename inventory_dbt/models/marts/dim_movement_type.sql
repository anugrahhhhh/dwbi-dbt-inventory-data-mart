-- dim_movement_type: tipe pergerakan + kelompok + tanda pengaruhnya terhadap stok.
-- TRANSFER bertanda 0 karena arahnya (keluar/masuk) ditentukan per baris oleh transfer_direction.
with types as (
    select distinct movement_type from {{ ref('stg_inventory_movements') }}
)
select
    cast(row_number() over (order by movement_type) as integer) as movement_type_key,
    movement_type,
    case
        when movement_type in ('PURCHASE', 'FOUND')        then 'inbound'
        when movement_type in ('SALE', 'LOST', 'DAMAGED')  then 'outbound'
        else 'transfer'
    end as movement_group,
    cast(case
        when movement_type in ('PURCHASE', 'FOUND')        then 1
        when movement_type in ('SALE', 'LOST', 'DAMAGED')  then -1
        else 0
    end as integer) as direction_sign
from types
