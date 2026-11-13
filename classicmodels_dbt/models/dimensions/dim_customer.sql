select
    row_number() over (order by c.customer_id) as customer_key,
    c.customer_id,
    c.customer_name,
    c.city,
    c.state,
    c.country,
    c.credit_limit,
    c.sales_rep_employee_id
from {{ ref('stg_customers') }} c
