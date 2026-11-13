-- Jumlah gudang per region
select
    region,
    count(*) as jumlah_gudang
from {{ ref('gudang') }}
group by region
