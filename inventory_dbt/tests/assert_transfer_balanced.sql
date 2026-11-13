-- Setiap transfer_id harus punya tepat 1 sisi OUT dan 1 sisi IN dengan quantity sama,
-- di dua gudang berbeda. Akibatnya total signed_quantity per transfer = 0.
select transfer_id,
       count(*)                                                     as jumlah_baris,
       sum(case when transfer_direction = 'OUT' then 1 else 0 end)  as jumlah_out,
       sum(case when transfer_direction = 'IN'  then 1 else 0 end)  as jumlah_in,
       count(distinct warehouse_key)                                as jumlah_gudang,
       sum(signed_quantity)                                         as total_signed
from {{ ref('fact_inventory') }}
where transfer_id is not null
group by transfer_id
having count(*) <> 2
    or sum(case when transfer_direction = 'OUT' then 1 else 0 end) <> 1
    or sum(case when transfer_direction = 'IN'  then 1 else 0 end) <> 1
    or count(distinct warehouse_key) <> 2
    or sum(signed_quantity) <> 0
