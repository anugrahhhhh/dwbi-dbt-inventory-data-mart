select
    productCode        as product_code,
    productName        as product_name,
    productLine        as product_line,
    productScale       as product_scale,
    productVendor      as product_vendor,
    productDescription as product_description,
    quantityInStock    as quantity_in_stock,
    buyPrice           as buy_price,
    MSRP               as msrp
from {{ source('classicmodels', 'products') }}
