# Catatan Elaborasi — ClassicModels: From OLTP to Data Marts

Sumber: `activity.html` (Data Warehouse Laboratory Activity, Semester 2025/2026).
Data: `mysqlsampledatabase.sql` asli dari MySQL Tutorial (diunduh 13 Nov 2026), dikonversi ke DuckDB oleh `load_source.py` (23 pernyataan, 0 galat).
Lingkungan: Python 3.10.6, dbt-core 1.11.17, dbt-duckdb 1.11.1, DuckDB 1.5.6.

## Langkah yang dikerjakan

| Langkah activity | Perintah | Hasil |
|---|---|---|
| Setup 1: pasang dependensi | `pip install "dbt-core~=1.11.0" "dbt-duckdb~=1.11.0" duckdb` | `dbt --version` → 1.11.17 / duckdb 1.11.1 |
| Setup 2: muat data | `python load_source.py` | `Done. Executed: 23 statements, Errors: 0` |
| Setup 3: cek koneksi | `dbt debug --profiles-dir .` | `All checks passed!` |
| Setup 4 / Step 1: eksplorasi | `python explore_source.py` | `[OK] All 8 expected tables found.` |
| Step 2–4: bangun model | `dbt build --profiles-dir .` | 16 model + 28 test → `PASS=44` |
| Step 5: business query | `python run_activity_queries.py` | `results/*.csv` |
| Step 6: DAG | `dbt docs generate` + `draw_diagrams.py` | `charts/lineage.png` |

## Jawaban pertanyaan terpandu (Part 1)

**BP1 — Sales Order Lines**
1. Setiap baris `orderdetails` mencatat satu produk dalam satu pesanan: kejadian paling rinci adalah *order line*.
2. Pesanan berisi 5 produk menghasilkan 5 baris, maka grain yang tepat adalah satu baris per *order line* (bukan per pesanan), supaya analisis per produk tidak kehilangan detail.
3. Pertanyaan "revenue Classic Cars Q3 2004 per kantor" membutuhkan `orderdetails`, `orders` (tanggal), `products`/`productlines` (lini produk), `customers` → `employees` → `offices` (kantor). Dimensi: tanggal, produk, pelanggan, sales rep, kantor.
4. Ukuran langsung: `quantity_ordered`, `price_each`; turunan: `revenue = qty × price_each`; dengan `products.buyPrice`: `cost` dan `gross_profit`.

**BP2 — Customer Payments**
1. Satu baris = satu cek pembayaran dari satu pelanggan. Ini peristiwa berbeda dari order line (pembayaran bisa terjadi berminggu-minggu setelah pesanan), sehingga butuh fakta sendiri agar tidak melanggar aturan satu grain.
2. Grain per transaksi pembayaran sudah cukup; total per bulan didapat dengan agregasi melalui `dim_date`.
3. Dimensi: tanggal dan pelanggan. Tidak adanya produk/pegawai bukan masalah: data sumber memang tidak mencatatnya; hubungan ke sales rep dapat ditelusuri lewat `dim_customer` (dimensi bersama).
4. Satu ukuran additive (`amount`) cukup; `check_number` disimpan sebagai *degenerate dimension*.

**BP3 — Sales Rep Performance**
1. Gabungkan `orderdetails` → `orders` → `customers` → `employees` (→ `offices`); di dbt cukup mengagregasi `fct_order_lines` (fact-on-fact).
2. Pilih (c) satu baris per sales rep per bulan: jauh lebih sedikit baris (218 vs 2.996) sehingga dashboard cepat, dengan konsekuensi detail per pesanan tidak tersedia di tabel ini.
3. Dimensi: pegawai (siapa), kantor/territory (di mana), bulan (kapan).
4. Ukuran: jumlah pesanan, pelanggan unik, unit terjual, revenue, gross profit, rata-rata revenue per baris.

## Checkpoint (semua lulus; diuji otomatis di `tests_py/test_checkpoints.py`)

- `dim_date`: 2003-01-01 s.d. 2006-12-31, 1.461 hari.
- `dim_employee`: semua pegawai punya manajer kecuali 1 (President).
- Classic Cars memiliki revenue tertinggi (USD 3.853.922,49).
- Total revenue sepanjang waktu USD 9.604.190,61 (≈ 9,6 juta).
- Top-5 sales rep 2004 memuat EMEA (Gerard Hernandez, Pamela Castillo, Barry Jones) dan APAC (Peter Marsh).
- Revenue bulanan memuncak pada November 2003 (USD 988.025) dan November 2004.
- Jumlah baris `fct_order_lines` = `orderdetails` (2.996).

## Temuan selama elaborasi

1. Dump MySQL perlu dikonversi: `FOREIGN KEY`, `mediumtext/mediumblob`, `smallint(6)`, dan escape `\'` tidak diterima DuckDB. Tabel dengan dua FOREIGN KEY (`employees`, `orderdetails`) sempat gagal karena regex awal hanya menghapus satu baris FK.
2. `dim_date` tidak dirujuk lewat `ref()` oleh fakta (fakta menyimpan tanggal langsung sebagai `order_date_id`), sehingga di DAG `dim_date` tampak berdiri sendiri. Integritasnya tetap dijaga dengan `relationships` test.
3. Kueri "Top sales reps in 2004" menjumlahkan `unique_customers` antarbulan. Kolom ini **non-additive**: pelanggan yang sama di dua bulan terhitung dua kali, sehingga `customers_served` adalah batas atas, bukan jumlah pelanggan unik sebenarnya.
4. Model activity memakai fungsi khusus DuckDB (`generate_series`, `strftime`, `::date`), sehingga tidak portabel ke PostgreSQL tanpa diubah. Proyek inventory kelompok sengaja ditulis portabel.
