select
    officeCode   as office_code,
    city         as city,
    phone        as phone,
    addressLine1 as address_line1,
    addressLine2 as address_line2,
    state        as state,
    country      as country,
    postalCode   as postal_code,
    territory    as territory
from {{ source('classicmodels', 'offices') }}
