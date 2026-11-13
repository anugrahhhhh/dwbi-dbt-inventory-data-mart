-- Grain snapshot lengkap: setiap produk x gudang x hari ada tepat satu baris
-- (termasuk hari tanpa transaksi, yang stoknya dibawa dari hari sebelumnya).
select jumlah_baris, seharusnya from (
    select (select count(*) from {{ ref('fact_inventory_daily_snapshot') }}) as jumlah_baris,
           (select count(*) from {{ ref('dim_product') }})
         * (select count(*) from {{ ref('dim_warehouse') }})
         * (select count(*) from {{ ref('dim_date') }}) as seharusnya
) x
where jumlah_baris <> seharusnya
