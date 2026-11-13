-- BQ8: Kategori produk mana yang paling banyak terjual (unit SALE)?
select
    p.category,
    count(*)        as sale_transactions,
    sum(f.quantity) as units_sold
from {{ ref('fact_inventory') }} f
join {{ ref('dim_product') }}       p on f.product_key = p.product_key
join {{ ref('dim_movement_type') }} t on f.movement_type_key = t.movement_type_key
where t.movement_type = 'SALE'
group by p.category
order by units_sold desc, p.category
