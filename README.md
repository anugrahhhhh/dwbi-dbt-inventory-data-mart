# Data Mart Inventory dengan dbt — Tugas II DWBI

Modul dan proyek **dbt (data build tool)** untuk membangun *Data Mart Inventory* berbasis
*star schema* (Kimball). Repositori ini berisi kode dbt yang dapat dijalankan, data sumber
sintetis, skrip pendukung (Extract & Load, *business query*, pembanding ETL manual, *mutation
test*), serta modul LaTeX yang menjelaskan semuanya untuk pembaca awam.

> Mata kuliah **Data Warehouse & Business Intelligence** — Magister Ilmu Komputer, Universitas Gadjah Mada.
> Tugas Kelompok II: *"dbt – Data Mart Inventory"*.

**Anggota kelompok:** Vytis Rabbani Rex · Muhammad Raihan Sinergie Proton · Alfat Raehan

---

## Daftar Isi

1. [Ringkasan](#ringkasan)
2. [Struktur Repositori](#struktur-repositori)
3. [Arsitektur Data Mart](#arsitektur-data-mart)
4. [Prasyarat](#prasyarat)
5. [Mulai Cepat (lokal, DuckDB)](#mulai-cepat-lokal-duckdb)
6. [Menjalankan di Google Colab + Neon PostgreSQL](#menjalankan-di-google-colab--neon-postgresql)
7. [Business Query BQ1–BQ9](#business-query-bq1bq9)
8. [Kualitas Data & Pengujian](#kualitas-data--pengujian)
9. [Pembanding dengan Tugas I (ETL manual)](#pembanding-dengan-tugas-i-etl-manual)
10. [Proyek Pendukung](#proyek-pendukung)
11. [Membangun Modul LaTeX (PDF)](#membangun-modul-latex-pdf)
12. [Membuat Berkas Lampiran (zip)](#membuat-berkas-lampiran-zip)
13. [Catatan & Batasan](#catatan--batasan)

---

## Ringkasan

| Aspek | Isi |
|---|---|
| Alat transformasi | dbt-core 1.11 (`dbt-duckdb` untuk lokal, `dbt-postgres` untuk Neon) |
| Basis data | DuckDB (lokal, tanpa server) **atau** PostgreSQL di [Neon](https://neon.tech) (via Google Colab) |
| Data sumber | 3 tabel OLTP: `source_products` (50 baris / 10 unik), `source_warehouses` (15 / 3 unik), `source_inventory_movements` (10.000 transaksi, 2024-01-01 s.d. 2025-12-31) |
| Model dbt | 9 model: 3 *staging* (view) + 4 dimensi + 2 fakta (table) |
| Pengujian | 50 *data test* (generic + 6 singular) — `dbt build` → `PASS=59` |
| Analisis | 9 *business query* (BQ1–BQ9) dengan hasil CSV dan grafik PNG |
| Dokumen | Modul LaTeX (Pendahuluan, Bab 1–3, Lampiran) dikompilasi menjadi `Makalah.pdf` |

---

## Struktur Repositori

```
.
├── inventory_dbt/                 # ★ Proyek utama: Data Mart Inventory
│   ├── dbt_project.yml            #   konfigurasi proyek (vars start_date/end_date)
│   ├── profiles.yml               #   target dev (DuckDB) & postgres (Neon, via env_var)
│   ├── data/                      #   CSV sumber hasil generate_source_data.py
│   ├── models/
│   │   ├── sources.yml            #   deklarasi sumber inventory_oltp
│   │   ├── staging/               #   stg_products, stg_warehouses, stg_inventory_movements
│   │   └── marts/                 #   dim_* , fact_inventory, fact_inventory_daily_snapshot
│   ├── macros/date_key.sql        #   makro pembuat date_key (YYYYMMDD)
│   ├── tests/                     #   6 singular test (dedup, rekonsiliasi, stok ≥ 0, transfer seimbang, …)
│   ├── analyses/                  #   bq1 … bq9 (SQL business query, memakai ref())
│   ├── scripts/                   #   skrip Python pendukung + tests/ (pytest)
│   ├── notebooks/                 #   inventory_dbt_colab.ipynb (panduan Colab + Neon)
│   ├── results/                   #   hasil BQ1–BQ9 (CSV)
│   ├── charts/                    #   grafik BQ1–BQ9 + lineage.png
│   └── logs/                      #   keluaran asli setiap perintah (bukti eksekusi)
│
├── classicmodels_dbt/             # Elaborasi lab "ClassicModels: From OLTP to Data Marts"
├── latihan_dbt/proyek_pertama/    # Latihan dbt dari nol (dbt init → seed → model → test)
│
├── Tugas II DWIB/Laporan Mahasiswa DWIB/   # Modul LaTeX
│   ├── Makalah.tex                #   berkas induk
│   ├── contents/                  #   Pendahuluan, Bab1, Bab2, Bab3, Lampiran
│   ├── figures/ , images/         #   gambar & grafik (disinkronkan oleh sync_assets.py)
│   ├── references.bib             #   daftar pustaka
│   ├── build.ps1                  #   kompilasi PDF (pdflatex + bibtex + makeindex)
│   ├── make_tables.py             #   tabel LaTeX otomatis dari results/*.csv
│   ├── sync_assets.py             #   salin grafik & kode ke folder modul
│   └── make_overleaf_zip.py       #   paket mandiri untuk diunggah ke Overleaf
│
├── docs/superpowers/              # Spesifikasi desain & rencana implementasi
├── activity.html/                 # Lembar aktivitas lab (sumber elaborasi ClassicModels)
├── DBT Presentation Slides.pdf    # Slide presentasi kelompok
├── make_zip.py                    # Membuat DWBI_Kelompok_Inventory.zip (lampiran)
└── requirements.txt               # Dependensi Python (versi terkunci)
```

---

## Arsitektur Data Mart

Alur ELT: **Extract & Load** dikerjakan oleh skrip Python (`load_source.py`), sedangkan
**Transform** sepenuhnya dikerjakan dbt.

```
data/*.csv ──load_source.py──▶ source_* (OLTP mentah)
                                   │
                         ┌─────────┴──────────┐  staging (view): trim spasi, string kosong → NULL, tipe data
                         ▼                    ▼
            stg_products / stg_warehouses   stg_inventory_movements
                         │                    │
         ┌───────────────┼──────────┐         │      marts (table)
         ▼               ▼          ▼         ▼
    dim_product   dim_warehouse  dim_date  dim_movement_type
         └───────────────┴──────────┴─────────┘
                         ▼
                  fact_inventory                    (grain: 1 baris = 1 pergerakan stok)
                         ▼
          fact_inventory_daily_snapshot             (grain: produk × gudang × hari, stok akhir hari)
```

| Model | Jenis | Keterangan |
|---|---|---|
| `dim_product` | dimensi | 10 produk unik; duplikat/versi lama dibuang (dedup) |
| `dim_warehouse` | dimensi | 3 gudang unik |
| `dim_date` | dimensi | kalender 731 hari (`vars.start_date` s.d. `vars.end_date`) |
| `dim_movement_type` | dimensi | 6 jenis: PURCHASE, SALE, TRANSFER, DAMAGED, LOST, FOUND |
| `fact_inventory` | *transaction fact* | 10.000 baris, satu baris per transaksi |
| `fact_inventory_daily_snapshot` | *periodic snapshot* | 21.930 baris (10 produk × 3 gudang × 731 hari) |

Diagram *lineage* lengkap: [`inventory_dbt/charts/lineage.png`](inventory_dbt/charts/lineage.png).

---

## Prasyarat

- **Python 3.10+** (diuji dengan 3.10.6)
- Git
- Opsional: akun [Neon](https://neon.tech) (PostgreSQL gratis) bila ingin memakai jalur Colab
- Opsional: TinyTeX / MiKTeX / TeX Live untuk mengompilasi modul PDF

Versi utama yang dipakai: `dbt-core 1.11.17`, `dbt-duckdb 1.11.1`, `dbt-postgres 1.11.0`,
`duckdb 1.5.6`, `pandas 2.3.3`, `matplotlib 3.10.9` (lihat [`requirements.txt`](requirements.txt)).

---

## Mulai Cepat (lokal, DuckDB)

Jalur ini tidak memerlukan server basis data apa pun.

```bash
# 1. Klon & siapkan lingkungan
git clone <url-repo-ini>
cd <nama-folder-repo>
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 2. Masuk ke proyek utama
cd inventory_dbt

# 3. (Opsional) bangkitkan ulang data sumber — CSV sudah tersedia di data/
python scripts/generate_source_data.py

# 4. Extract & Load: CSV → inventory.duckdb
python scripts/load_source.py

# 5. Cek koneksi dbt
dbt debug --profiles-dir .

# 6. Bangun seluruh model + jalankan semua test
dbt build --profiles-dir .
#    → Done. PASS=59 WARN=0 ERROR=0 SKIP=0 TOTAL=59

# 7. Jalankan business query BQ1–BQ9 (hasil ke results/ dan charts/)
python scripts/run_business_queries.py

# 8. Dokumentasi & lineage
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .        # buka di peramban
python scripts/draw_diagrams.py        # simpan charts/lineage.png
```

> `profiles.yml` disimpan di dalam folder proyek, karena itu setiap perintah dbt memakai
> `--profiles-dir .`. Lokasi berkas DuckDB dapat diubah dengan variabel lingkungan
> `INVENTORY_DB` (bawaan: `inventory.duckdb`).

---

## Menjalankan di Google Colab + Neon PostgreSQL

Panduan langkah demi langkah tersedia di notebook
[`inventory_dbt/notebooks/inventory_dbt_colab.ipynb`](inventory_dbt/notebooks/inventory_dbt_colab.ipynb).

Ringkasnya:

1. Buat proyek di [neon.tech](https://neon.tech) dan salin *connection string*.
2. Di Colab, simpan kredensial sebagai **Secrets**: `NEON_HOST`, `NEON_USER`, `NEON_PASSWORD`, `NEON_DB`
   (aktifkan *Notebook access*). Jika dijalankan di luar Colab, set sebagai variabel lingkungan.
3. Unggah/ekstrak proyek, lalu jalankan:

```bash
pip install "dbt-core~=1.11.0" "dbt-postgres~=1.11.0" psycopg2-binary pandas matplotlib
cd inventory_dbt
python scripts/load_source.py --target postgres        # tabel source_* di skema public
dbt debug --profiles-dir . --target postgres
dbt build --profiles-dir . --target postgres           # model dibuat di skema analytics_dbt
python scripts/run_business_queries.py --target postgres
```

🔒 **Kredensial tidak pernah ditulis di berkas mana pun.** `profiles.yml` membacanya dengan
`env_var()`, dan `scripts/tests/test_portability.py` memeriksa bahwa tidak ada kata sandi tertulis.

---

## Business Query BQ1–BQ9

Semua query ada di [`inventory_dbt/analyses/`](inventory_dbt/analyses/) dan memakai `ref()`,
sehingga `dbt compile` merendernya menjadi SQL murni untuk target mana pun.

| # | Pertanyaan bisnis | Hasil | Grafik |
|---|---|---|---|
| BQ1 | Rata-rata hari stok tertahan per gudang (*inventory aging*) | [csv](inventory_dbt/results/bq1_aging_by_warehouse.csv) | [png](inventory_dbt/charts/bq1_aging_by_warehouse.png) |
| BQ2 | Distribusi (proporsi) aktivitas per jenis pergerakan | [csv](inventory_dbt/results/bq2_activity_distribution.csv) | [png](inventory_dbt/charts/bq2_activity_distribution.png) |
| BQ3 | Peta aktivitas jenis pergerakan × gudang (matriks) | [csv](inventory_dbt/results/bq3_activity_heatmap.csv) | [png](inventory_dbt/charts/bq3_activity_heatmap.png) |
| BQ4 | Jumlah aktivitas per gudang & jenis pergerakan | [csv](inventory_dbt/results/bq4_activity_by_warehouse.csv) | [png](inventory_dbt/charts/bq4_activity_by_warehouse.png) |
| BQ5 | *Inventory aging* per kategori produk di setiap gudang | [csv](inventory_dbt/results/bq5_aging_by_category_warehouse.csv) | [png](inventory_dbt/charts/bq5_aging_by_category_warehouse.png) |
| BQ6 | Unit hilang (LOST) & rusak (DAMAGED) per kategori & gudang | [csv](inventory_dbt/results/bq6_lost_damaged.csv) | [png](inventory_dbt/charts/bq6_lost_damaged.png) |
| BQ7 | Total aktivitas per jenis pergerakan | [csv](inventory_dbt/results/bq7_total_activity.csv) | [png](inventory_dbt/charts/bq7_total_activity.png) |
| BQ8 | Kategori produk dengan unit terjual terbanyak | [csv](inventory_dbt/results/bq8_units_sold_by_category.csv) | [png](inventory_dbt/charts/bq8_units_sold_by_category.png) |
| BQ9 | Jumlah transfer antargudang per bulan | [csv](inventory_dbt/results/bq9_transfers_per_month.csv) | [png](inventory_dbt/charts/bq9_transfers_per_month.png) |

Contoh hasil BQ7:

| movement_type | total_activity | total_units |
|---|---:|---:|
| TRANSFER | 3.310 | 57.512 |
| DAMAGED | 1.691 | 11.926 |
| LOST | 1.691 | 11.718 |
| PURCHASE | 1.673 | 83.939 |
| SALE | 1.602 | 28.094 |
| FOUND | 33 | 91 |

---

## Kualitas Data & Pengujian

### Data test dbt (50 test)

- **Generic test** di `schema.yml`: `unique`, `not_null`, `accepted_values`, `relationships`
  (setiap kunci asing fakta → dimensi).
- **Singular test** di [`inventory_dbt/tests/`](inventory_dbt/tests/):

| Test | Yang diperiksa |
|---|---|
| `assert_dimension_dedup` | dimensi tidak mengandung duplikat natural key |
| `assert_fact_row_count_matches_source` | jumlah baris fakta = jumlah transaksi sumber |
| `assert_snapshot_grain_complete` | snapshot lengkap untuk setiap produk × gudang × hari |
| `assert_snapshot_reconciles_fact` | stok snapshot cocok dengan akumulasi fakta |
| `assert_stock_non_negative` | stok tidak pernah negatif |
| `assert_transfer_balanced` | sisi OUT dan IN setiap transfer sama besar |

### Mutation test

`python scripts/mutation_test.py` menyuntikkan kerusakan ke **salinan terpisah** basis data
dan membuktikan bahwa setiap singular test benar-benar gagal pada kerusakan miliknya
(dan tetap lulus pada kerusakan lain). Hasil: `KESIMPULAN: SEMUA TEST MENDETEKSI KERUSAKAN`
(lihat [`logs/mutation_test.txt`](inventory_dbt/logs/mutation_test.txt)).

### Unit test Python (pytest)

```bash
cd inventory_dbt
pytest scripts/tests -q
```

Mencakup pembangkit data, *loader* PostgreSQL, *business query*, diagram, pembanding,
*mutation test*, portabilitas `profiles.yml`, dan pemeriksa angka modul.

### Pemeriksa angka modul

`python scripts/check_numbers.py "../Tugas II DWIB/Laporan Mahasiswa DWIB/contents/Bab3.tex"`
memastikan setiap angka yang disebut di narasi modul benar-benar muncul di hasil eksekusi.

---

## Pembanding dengan Tugas I (ETL manual)

Untuk menunjukkan nilai tambah dbt, data mart yang sama dibangun ulang dengan gaya Tugas I
(DDL + `INSERT … SELECT` ditulis tangan di Python, urutan eksekusi diatur manual):

```bash
cd inventory_dbt
python scripts/etl_manual_tugas1.py              # → inventory_tugas1.duckdb
python scripts/compare_tugas1_vs_dbt.py          # bandingkan per baris dengan hasil dbt
```

- **Versi normal** → seluruh dimensi, fakta, snapshot, dan BQ1–BQ9 **IDENTIK**
  ([`logs/compare_normal.txt`](inventory_dbt/logs/compare_normal.txt)).
- **Versi naif** (`--naive`, dimensi tanpa dedup) → hasil **BERBEDA**, misalnya BQ5/BQ6 menjadi
  48 baris alih-alih 24 ([`logs/compare_naive.txt`](inventory_dbt/logs/compare_naive.txt)).
  Kesalahan seperti ini ditangkap otomatis oleh test dbt.

---

## Proyek Pendukung

### `classicmodels_dbt/` — Elaborasi lab ClassicModels

Mengerjakan lembar aktivitas *"ClassicModels: From OLTP to Data Marts"* dengan data
`mysqlsampledatabase.sql` asli, dikonversi ke DuckDB.

```bash
cd classicmodels_dbt
python load_source.py
dbt debug --profiles-dir .
python explore_source.py
dbt build --profiles-dir .           # 16 model + 28 test → PASS=44
python run_activity_queries.py       # hasil ke results/*.csv
pytest tests_py -q                   # checkpoint lab
```

Jawaban pertanyaan terpandu dan tabel langkah ada di
[`classicmodels_dbt/ACTIVITY_NOTES.md`](classicmodels_dbt/ACTIVITY_NOTES.md).
Fakta yang dibangun: `fct_order_lines`, `fct_payments`, `fct_sales_performance`.

### `latihan_dbt/proyek_pertama/` — Latihan dari nol

Proyek kecil hasil `dbt init` untuk pemula: *seed* `gudang.csv`, model `gudang_per_region`,
dan contoh test yang sengaja gagal. Keluaran tiap langkah tersimpan di `latihan_dbt/logs/`.

```bash
cd latihan_dbt/proyek_pertama
dbt build --profiles-dir .
```

---

## Membangun Modul LaTeX (PDF)

Modul berada di `Tugas II DWIB/Laporan Mahasiswa DWIB/`.

**Windows (PowerShell):**

```powershell
cd "Tugas II DWIB\Laporan Mahasiswa DWIB"
.\build.ps1          # sync_assets.py → pdflatex → bibtex → makeindex → pdflatex ×2
```

Skrip otomatis memakai TinyTeX di `%APPDATA%\TinyTeX` jika ada, menyinkronkan grafik dan
kode dari `inventory_dbt/`, lalu melaporkan galat LaTeX atau referensi yang belum terdefinisi.

**Overleaf:** jalankan `python make_overleaf_zip.py` untuk menghasilkan `Modul_Overleaf.zip`
yang mandiri, lalu unggah sebagai proyek baru di Overleaf.

Tabel hasil di Bab 3 dibangkitkan otomatis dari `results/*.csv` oleh `make_tables.py`, sehingga
angka di modul selalu sama dengan hasil eksekusi.

> `Makalah.pdf`, berkas bantu LaTeX, dan folder `kode/` hasil sinkronisasi tidak disimpan di
> repositori (lihat `.gitignore`); bangun ulang dengan `build.ps1`.

---

## Membuat Berkas Lampiran (zip)

```bash
python make_zip.py     # → DWBI_Kelompok_Inventory.zip
```

Berisi `inventory_dbt/`, `classicmodels_dbt/`, `latihan_dbt/`, folder modul, dan
`requirements.txt`, tanpa berkas besar/sementara (`.venv`, `*.duckdb`, `target/`, cache, berkas bantu LaTeX).

---

## Catatan & Batasan

- **Data sintetis.** Berkas proyek asli Tugas I tidak tersedia, sehingga data sumber dibangkitkan
  ulang oleh `generate_source_data.py` mengikuti desain pada slide ("Database Sumber (OLTP)").
  Akibatnya, angka di repositori ini dapat berbeda dari angka di `DBT Presentation Slides.pdf`.
- Data sengaja memuat "kotoran" (spasi berlebih, string kosong, duplikat versi lama) agar
  lapisan *staging* dan dedup dimensi memiliki pekerjaan nyata.
- Berkas `*.duckdb`, `target/`, dan `logs/dbt.log` diabaikan oleh Git; jalankan ulang
  langkah-langkah di atas untuk membuatnya kembali.
- `Modul_dbt_Kelompok_Transportation_revisi.pdf` adalah modul kelompok lain yang dipakai sebagai
  acuan gaya penulisan, bukan karya kelompok ini.
