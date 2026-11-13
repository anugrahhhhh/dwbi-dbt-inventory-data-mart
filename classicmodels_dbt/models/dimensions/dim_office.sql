select
    row_number() over (order by o.office_code) as office_key,
    o.office_code,
    o.city,
    o.state,
    o.country,
    o.territory
from {{ ref('stg_offices') }} o
