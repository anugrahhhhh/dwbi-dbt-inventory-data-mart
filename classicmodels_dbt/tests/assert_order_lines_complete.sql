-- Tidak ada baris orderdetails yang hilang saat join ke dimensi (PASS bila 0 baris).
select sumber, fakta from (
    select (select count(*) from {{ source('classicmodels', 'orderdetails') }}) as sumber,
           (select count(*) from {{ ref('fct_order_lines') }}) as fakta
) x where sumber <> fakta
