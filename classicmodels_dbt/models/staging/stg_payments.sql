select
    customerNumber as customer_id,
    checkNumber    as check_number,
    paymentDate    as payment_date,
    amount         as amount
from {{ source('classicmodels', 'payments') }}
