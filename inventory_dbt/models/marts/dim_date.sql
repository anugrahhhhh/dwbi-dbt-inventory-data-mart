-- dim_date: kalender penuh dari var start_date s.d. end_date (recursive CTE, portabel).
with recursive days as (
    select cast('{{ var("start_date") }}' as date) as d
    union all
    select cast(d + interval '1 day' as date) from days
    where d < cast('{{ var("end_date") }}' as date)
)
select
    {{ date_key('d') }}                                   as date_key,     -- smart key YYYYMMDD
    d                                                     as full_date,
    cast(extract(year from d) as integer)                 as year,
    cast(extract(quarter from d) as integer)              as quarter,
    cast(extract(month from d) as integer)                as month,
    case cast(extract(month from d) as integer)
        when 1 then 'Januari' when 2 then 'Februari' when 3 then 'Maret'
        when 4 then 'April' when 5 then 'Mei' when 6 then 'Juni'
        when 7 then 'Juli' when 8 then 'Agustus' when 9 then 'September'
        when 10 then 'Oktober' when 11 then 'November' else 'Desember'
    end                                                   as month_name,
    cast(extract(week from d) as integer)                 as week_of_year,
    cast(extract(day from d) as integer)                  as day_of_month,
    cast(extract(dow from d) as integer)                  as day_of_week,  -- 0 = Minggu
    case cast(extract(dow from d) as integer)
        when 0 then 'Minggu' when 1 then 'Senin' when 2 then 'Selasa'
        when 3 then 'Rabu' when 4 then 'Kamis' when 5 then 'Jumat' else 'Sabtu'
    end                                                   as day_name,
    extract(dow from d) in (0, 6)                         as is_weekend
from days
