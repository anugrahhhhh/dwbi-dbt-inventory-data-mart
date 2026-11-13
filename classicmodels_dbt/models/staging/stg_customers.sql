select
    customerNumber         as customer_id,
    customerName           as customer_name,
    contactLastName        as contact_last_name,
    contactFirstName       as contact_first_name,
    phone                  as phone,
    addressLine1           as address_line1,
    addressLine2           as address_line2,
    city                   as city,
    state                  as state,
    postalCode             as postal_code,
    country                as country,
    salesRepEmployeeNumber as sales_rep_employee_id,
    creditLimit            as credit_limit
from {{ source('classicmodels', 'customers') }}
