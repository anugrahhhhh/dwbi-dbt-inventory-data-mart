select
    productLine     as product_line,
    textDescription as text_description
from {{ source('classicmodels', 'productlines') }}
