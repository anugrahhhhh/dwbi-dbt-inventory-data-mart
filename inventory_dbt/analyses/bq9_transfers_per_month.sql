-- BQ9: Berapa transaksi transfer antargudang setiap bulan?
-- Satu transfer = dua baris (OUT & IN), maka dihitung COUNT(DISTINCT transfer_id).
select
    d.year,
    d.month,
    count(distinct f.transfer_id) as transfer_count,
    sum(case when f.transfer_direction = 'OUT' then f.quantity else 0 end) as units_transferred
from {{ ref('fact_inventory') }} f
join {{ ref('dim_date') }} d on f.date_key = d.date_key
where f.transfer_id is not null
group by d.year, d.month
order by d.year, d.month
