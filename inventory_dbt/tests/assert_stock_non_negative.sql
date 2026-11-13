-- Stok fisik tidak mungkin negatif pada hari mana pun.
select date_key, product_key, warehouse_key, stock_on_hand
from {{ ref('fact_inventory_daily_snapshot') }}
where stock_on_hand < 0
