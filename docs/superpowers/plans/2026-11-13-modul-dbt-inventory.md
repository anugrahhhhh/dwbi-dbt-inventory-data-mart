# Modul dbt Inventory — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun ulang proyek dbt Data Mart Inventory (+ elaborasi ClassicModels), menjalankannya sungguhan, lalu menulis modul LaTeX Tugas II DWBI yang memakai kode dan angka dari eksekusi tersebut.

**Architecture:** Python membangkitkan dan memuat 3 tabel sumber ke DuckDB. dbt membangun staging (view), lalu dimensi dan dua fakta (table), menjalankan test, dan mengompilasi BQ1–9 di `analyses/`. Skrip Python menjalankan BQ dan membuat grafik. Modul LaTeX (template `kultem`) mengutip berkas hasil (`results/*.csv`, log, PNG). SQL dijaga portabel agar target `postgres` (Colab + Neon) terkompilasi.

**Tech Stack:** Python 3.10 (venv), dbt-core + dbt-duckdb + dbt-postgres (minor terkunci), DuckDB, pandas, matplotlib, pytest, TinyTeX (pdflatex + bibtex + makeindex).

**Spec:** `docs/superpowers/specs/2026-11-13-modul-dbt-inventory-design.md`

## Global Constraints

- Root kerja: `c:\Users\ASUS\Downloads\alfat dtwh` (path mengandung spasi; selalu dikutip).
- Semua kode, keluaran terminal, dan angka di modul berasal dari eksekusi nyata; dilarang mengarang angka.
- Versi dbt dikunci ke rilis stabil (bukan rc/beta). Coba `dbt-core~=1.10.0`, `dbt-duckdb~=1.10.0`, `dbt-postgres~=1.10.0`; bila tidak dapat di-resolve, pakai minor stabil tertinggi yang didukung ketiganya. Catat di `requirements.txt`.
- Seed generator data = `42`. Periode data 2024-01-01 s.d. 2025-12-31 (731 hari).
- Tidak ada password/kredensial di berkas mana pun; target postgres memakai `env_var('NEON_HOST')`, `env_var('NEON_USER')`, `env_var('NEON_PASSWORD')`, `env_var('NEON_DB')`.
- Bahasa modul: Bahasa Indonesia baku; istilah teknis Inggris dicetak miring saat pertama muncul.
- Anggota dan peran: Vytis Rabbani Rex (26/590730/PPA/07412) = Data Modeler; Muhammad Raihan Sinergie Proton (26/591068/PPA/07429) = dbt & Pipeline Engineer; Alfat Raehan (26/590022/PPA/0738, NIM ditandai untuk dikonfirmasi pengguna) = Documentation & QA Lead.
- Folder ini belum repo git: Task 1 menjalankan `git init`; setiap task diakhiri commit lokal (tanpa push).

## Review Focus

1. **Path dengan spasi** (`alfat dtwh`): semua perintah di modul dan skrip harus jalan dari PowerShell. Skrip memakai `pathlib` relatif terhadap lokasi skrip; perintah di modul dikutip. Test: Task 2 menjalankan generator dari direktori lain.
2. **Menjalankan ulang** generator/loader/dbt dua kali harus menghasilkan tabel yang sama, bukan baris ganda. Test: Task 2 `test_load_is_idempotent`.
3. **Hari tanpa movement** pada snapshot tetap memiliki baris dengan stok terbawa (*carry forward*). Test: Task 4 snapshot = 10 × 3 × 731 = 21.930 baris, dan singular test rekonsiliasi.
4. **Pembagian nol** pada aging bila `qty_out` = 0 → hasil NULL, bukan galat. Test: Task 5 BQ1/BQ5 memakai `NULLIF`; pytest memastikan tidak ada `inf`.
5. **Dialek PostgreSQL**: fungsi tanggal, pembagian bilangan bulat, dan `generate_series` berbeda dari DuckDB. Test: Task 7 `dbt compile --target postgres` sukses, ditambah pemeriksaan grep fungsi khusus DuckDB.

---

## File Structure

```
alfat dtwh/
├── requirements.txt, .gitignore
├── inventory_dbt/
│   ├── dbt_project.yml, profiles.yml, packages: none
│   ├── macros/date_key.sql                 # date_key(col) -> INT YYYYMMDD, adapter.dispatch duckdb/postgres
│   ├── models/sources.yml
│   ├── models/staging/{stg_products,stg_warehouses,stg_inventory_movements}.sql, schema.yml
│   ├── models/marts/{dim_date,dim_product,dim_warehouse,dim_movement_type,fact_inventory,fact_inventory_daily_snapshot}.sql, schema.yml
│   ├── tests/assert_*.sql                  # 5 singular tests
│   ├── analyses/bq1_aging_by_warehouse.sql … bq9_transfers_per_month.sql
│   ├── scripts/{generate_source_data,load_source,run_business_queries,etl_manual_tugas1,compare_tugas1_vs_dbt,mutation_test,draw_diagrams}.py
│   ├── scripts/tests/test_*.py             # pytest
│   ├── data/*.csv, results/*.csv, charts/*.png, logs/*.txt
│   └── notebooks/inventory_dbt_colab.ipynb
├── classicmodels_dbt/                      # mengikuti activity.html
└── Tugas II DWIB/Laporan Mahasiswa DWIB/
    ├── Makalah.tex (diubah), references.bib (diganti)
    ├── contents/{Pendahuluan,Bab1,Bab2,Bab3,Lampiran}.tex
    └── figures/*.png
```

## Data Contracts (dipakai lintas task)

**Sumber (tabel DuckDB `inventory.duckdb`, schema `main`):**
- `source_products(product_id TEXT, product_name TEXT, category TEXT, brand TEXT, product_status TEXT, updated_at TIMESTAMP)`
- `source_warehouses(warehouse_id TEXT, warehouse_name TEXT, city TEXT, region TEXT, warehouse_type TEXT, updated_at TIMESTAMP)`
- `source_inventory_movements(transaction_id TEXT, transfer_id TEXT NULL, transfer_direction TEXT NULL /*'OUT'|'IN'*/, product_id TEXT, warehouse_id TEXT, movement_type TEXT, quantity INTEGER, transaction_timestamp TIMESTAMP)`

**Marts:**
- `dim_product(product_key INT, product_id, product_name, category, brand, product_status)`
- `dim_warehouse(warehouse_key INT, warehouse_id, warehouse_name, city, region, warehouse_type)`
- `dim_movement_type(movement_type_key INT, movement_type, movement_group /*inbound|outbound|transfer*/, direction_sign INT /*+1, -1, 0 untuk TRANSFER*/)`
- `dim_date(date_key INT, full_date DATE, year, quarter, month, month_name, week_of_year, day_of_month, day_of_week, day_name, is_weekend BOOLEAN)`
- `fact_inventory(transaction_id, transfer_id, transfer_direction, date_key, product_key, warehouse_key, movement_type_key, transaction_timestamp, quantity BIGINT, signed_quantity BIGINT)`; `signed_quantity` = +quantity untuk PURCHASE/FOUND/TRANSFER-IN, −quantity untuk SALE/LOST/DAMAGED/TRANSFER-OUT.
- `fact_inventory_daily_snapshot(date_key, product_key, warehouse_key, qty_in BIGINT, qty_out BIGINT, net_change BIGINT, stock_on_hand BIGINT)`; grain produk × gudang × hari, 21.930 baris.

---

### Task 1: Lingkungan dan kerangka repo

**Files:**
- Create: `requirements.txt`, `.gitignore` (`.venv/`, `*.duckdb`, `target/`, `logs/dbt.log`, `dbt_packages/`, LaTeX aux)

**Interfaces:**
- Produces: `.venv` dengan `dbt`, `pytest`, `duckdb`, `pandas`, `matplotlib` di PATH saat venv aktif.

- [ ] **Step 1:** `git init` di root; buat `.gitignore`.
- [ ] **Step 2:** Buat `.venv` dengan `py -3.10 -m venv .venv` (atau `python -m venv`, Python 3.10.6), lalu pasang versi terkunci sesuai Global Constraints, ditambah `duckdb pandas matplotlib pytest nbformat`.
- [ ] **Step 3: Verifikasi.** `dbt --version` menampilkan Core stabil, dengan plugin `duckdb` dan `postgres` pada minor yang sama. Simpan keluaran ke `inventory_dbt/logs/dbt_version.txt` (akan dikutip di Bab 2). `pip freeze > requirements.txt`.
- [ ] **Step 4:** Commit `chore: environment and repo scaffold`.

### Task 2: Generator dan loader data sumber

**Files:**
- Create: `inventory_dbt/scripts/generate_source_data.py`, `inventory_dbt/scripts/load_source.py`
- Test: `inventory_dbt/scripts/tests/test_source_data.py`

**Interfaces:**
- Produces: `generate(out_dir: Path, seed: int = 42) -> dict[str, pd.DataFrame]` (menulis `data/source_*.csv`); `load(db_path: Path, data_dir: Path) -> dict[str, int]` (CREATE OR REPLACE ketiga tabel, mengembalikan jumlah baris). CLI: `python scripts/generate_source_data.py` dan `python scripts/load_source.py` (default path relatif ke folder proyek).

- [ ] **Step 1: Tulis test yang gagal.**

```python
def test_counts(dfs):
    assert len(dfs["source_products"]) == 50 and dfs["source_products"].product_id.nunique() == 10
    assert len(dfs["source_warehouses"]) == 15 and dfs["source_warehouses"].warehouse_id.nunique() == 3
    assert len(dfs["source_inventory_movements"]) == 10_000
    assert dfs["source_inventory_movements"].transaction_id.is_unique

def test_categories(dfs):
    latest = dfs["source_products"].sort_values("updated_at").groupby("product_id").tail(1)
    assert set(latest.category.str.strip()) == {"Air Fryer","Blender","Coffee Maker","Electric Kettle",
        "Electric Stove","Hand Mixer","Microwave","Rice Cooker"}
    assert set(dfs["source_warehouses"].warehouse_name.str.strip().unique()) >= {"Warehouse Jawa","Warehouse Sumatra","Warehouse Kalimantan"}

def test_movement_mix(dfs):
    m = dfs["source_inventory_movements"]
    assert set(m.movement_type) == {"PURCHASE","SALE","TRANSFER","LOST","DAMAGED","FOUND"}
    share = m.movement_type.value_counts(normalize=True)
    assert 0.30 <= share["TRANSFER"] <= 0.36 and share["FOUND"] < 0.01
    assert m.transaction_timestamp.min() >= pd.Timestamp("2024-01-01") and m.transaction_timestamp.max() < pd.Timestamp("2026-01-01")

def test_transfer_pairs(dfs):
    t = dfs["source_inventory_movements"].query("movement_type == 'TRANSFER'")
    g = t.groupby("transfer_id")
    assert (g.size() == 2).all() and (g.transfer_direction.apply(set) == {"OUT","IN"}).all()
    assert (g.quantity.nunique() == 1).all() and (g.warehouse_id.nunique() == 2).all()

def test_stock_never_negative(dfs): ...   # running sum signed qty per (product, warehouse) sorted by timestamp >= 0

def test_dirty_values_present(dfs):       # untuk mendemokan TRIM/NULLIF di staging
    p = dfs["source_products"]
    assert (p.product_name != p.product_name.str.strip()).any() and (p.brand == "").any()

def test_load_is_idempotent(tmp_path): load twice -> counts equal {50, 15, 10000}
def test_runs_from_other_cwd(tmp_path): subprocess generate script with cwd=tmp_path -> exit 0
```

- [ ] **Step 2:** `pytest inventory_dbt/scripts/tests -q` → FAIL (modul belum ada).
- [ ] **Step 3: Implementasi.** Tanggal movement diurutkan secara kronologis. Movement keluar (SALE, LOST, DAMAGED, TRANSFER-OUT) hanya dibuat bila stok gudang mencukupi; bila tidak, ganti dengan PURCHASE. Gunakan target proporsi ±16,7% untuk PURCHASE/SALE/LOST/DAMAGED, ±33% TRANSFER (baris), dan ±0,3% FOUND. Duplikat produk/gudang memakai `updated_at` lebih lama dan sebagian berisi spasi berlebih atau string kosong.
- [ ] **Step 4:** `pytest` → PASS. Jalankan kedua CLI dan simpan keluarannya ke `logs/generate_load.txt`.
- [ ] **Step 5:** Commit `feat: synthetic inventory source data`.

### Task 3: Proyek dbt — source, staging, dimensi

**Files:**
- Create: `inventory_dbt/dbt_project.yml` (nama `inventory_dbt`; `staging: +materialized: view`, `marts: +materialized: table`), `profiles.yml` (profil `inventory_dbt`, target `dev` = duckdb `path: inventory.duckdb`, threads 4; target `postgres` = env_var, schema `analytics_dbt`, threads 4), `macros/date_key.sql`, `models/sources.yml`, staging ×3 + `schema.yml`, `dim_product`, `dim_warehouse`, `dim_movement_type`, `dim_date`, `models/marts/schema.yml` (bagian dimensi).

**Interfaces:**
- Consumes: tabel sumber (Data Contracts).
- Produces: model dimensi sesuai Data Contracts; macro `date_key(column)`.

- [ ] **Step 1: Test terlebih dahulu (YAML).** Pasang source test `unique` dan `not_null` pada `transaction_id`. Pasang `unique` dan `not_null` pada setiap surrogate key dan natural key dimensi. Pasang `accepted_values` pada `dim_movement_type.movement_type` (6 nilai) dan `stg_inventory_movements.transfer_direction` (`OUT`, `IN`, nilai NULL diabaikan). Tambahkan singular `tests/assert_dimension_dedup.sql`: jumlah baris `dim_product`/`dim_warehouse` = jumlah id unik non-NULL di sumber.
- [ ] **Step 2:** `dbt build --profiles-dir . --select staging dim_product dim_warehouse dim_movement_type dim_date` → ERROR/FAIL karena model belum ada.
- [ ] **Step 3: Implementasi.** Staging memakai `TRIM`, `NULLIF(TRIM(x), '')`, cast `quantity` BIGINT, dan `UPPER(TRIM(movement_type))`. Dimensi produk/gudang mengikuti SCD 1 seperti slide 17 (`ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC NULLS LAST)`, `WHERE row_num = 1`, surrogate key `ROW_NUMBER() OVER (ORDER BY id)`). `dim_date` dibangkitkan untuk 2024-01-01..2025-12-31 dengan recursive CTE (portabel, tanpa `generate_series`). `dim_movement_type` diturunkan dari staging dengan nilai CASE untuk `movement_group` dan `direction_sign`.
- [ ] **Step 4:** Perintah yang sama → PASS. Periksa `dim_date` = 731 baris, `dim_product` = 10, `dim_warehouse` = 3, `dim_movement_type` = 6.
- [ ] **Step 5:** Commit `feat: dbt staging and dimensions`.

### Task 4: Fakta, snapshot, singular test, mutation test

**Files:**
- Create: `models/marts/fact_inventory.sql`, `models/marts/fact_inventory_daily_snapshot.sql`, bagian fakta di `models/marts/schema.yml`, `tests/assert_fact_row_count_matches_source.sql`, `tests/assert_transfer_balanced.sql`, `tests/assert_stock_non_negative.sql`, `tests/assert_snapshot_reconciles_fact.sql`, `scripts/mutation_test.py`

**Interfaces:**
- Consumes: dimensi dari Task 3.
- Produces: kedua fakta (Data Contracts); `mutation_test.py` yang mencetak tabel `test | expected FAIL | actual` dan keluar dengan kode 0 bila semua test benar-benar FAIL pada data rusak.

- [ ] **Step 1: Test terlebih dahulu.** Generic: `not_null` dan `relationships` untuk ke-4 FK `fact_inventory` (date, product, warehouse, movement_type) dan ke-3 FK snapshot; `unique` pada `fact_inventory.transaction_id`. Singular:
  - row count fakta = sumber (10.000);
  - setiap `transfer_id` punya tepat 1 OUT dan 1 IN dengan quantity sama;
  - `stock_on_hand >= 0`;
  - stok pada `date_key = 20251231` per produk × gudang = Σ `signed_quantity` fakta;
  - jumlah baris snapshot = (#produk × #gudang × #hari).
- [ ] **Step 2:** `dbt build --profiles-dir .` → gagal karena model fakta belum ada.
- [ ] **Step 3: Implementasi.** `fact_inventory` melakukan join staging ke dimensi lewat natural key. `date_key` diambil via macro, dan `signed_quantity` dari `direction_sign` (TRANSFER memakai `transfer_direction`). Snapshot adalah *cross join* `dim_date` × kombinasi produk × gudang, lalu *left join* agregat harian `qty_in`/`qty_out`, dan `stock_on_hand = SUM(net_change) OVER (PARTITION BY product_key, warehouse_key ORDER BY date_key ROWS UNBOUNDED PRECEDING)`.
- [ ] **Step 4:** `dbt build --profiles-dir .` → semua PASS. Simpan keluaran lengkap ke `logs/dbt_build.txt` dan catat jumlah model/test. Jalankan `dbt docs generate`. Buat `scripts/draw_diagrams.py` yang membaca `target/manifest.json` dan menggambar lineage ke `charts/lineage.png`, serta menggambar star schema kedua fakta ke `charts/star_fact_inventory.png` dan `charts/star_snapshot.png`.
- [ ] **Step 5:** Tulis `mutation_test.py`. Skrip menyalin DB ke berkas sementara, merusak data (hapus satu sisi transfer, ubah satu SALE menjadi quantity yang sangat besar), lalu menjalankan `dbt test` dengan `--vars` atau target yang menunjuk ke salinan. Hasil yang diharapkan: `assert_transfer_balanced` dan `assert_stock_non_negative` FAIL. Simpan keluarannya ke `logs/mutation_test.txt`.
- [ ] **Step 6:** Commit `feat: inventory facts, snapshot, and data tests`.

### Task 5: Business query BQ1–BQ9 dan grafik

**Files:**
- Create: `analyses/bq1_aging_by_warehouse.sql`, `bq2_activity_distribution.sql`, `bq3_activity_heatmap.sql`, `bq4_activity_by_warehouse.sql`, `bq5_aging_by_category_warehouse.sql`, `bq6_lost_damaged.sql`, `bq7_total_activity.sql`, `bq8_units_sold_by_category.sql`, `bq9_transfers_per_month.sql`, `scripts/run_business_queries.py`
- Test: `scripts/tests/test_business_queries.py`

**Interfaces:**
- Consumes: kedua fakta dan dimensi.
- Produces: `results/bqN_*.csv` dan `charts/bqN_*.png` (nama dasar sama dengan berkas analysis). `run_business_queries.py` menjalankan `dbt compile --select "analyses/*"` lalu mengeksekusi SQL dari `target/compiled/inventory_dbt/analyses/`.

- [ ] **Step 1: Tulis test yang gagal.** Ada 9 CSV dan 9 PNG. BQ7: Σ jumlah aktivitas = 10.000. BQ2: Σ persentase = 100 ± 0,1. BQ3 = BQ4 setelah pivot. BQ8: Σ unit = Σ quantity SALE dari tabel sumber. BQ9: 24 bulan dan Σ = jumlah `transfer_id` unik. BQ1/BQ5: tidak ada `inf`, nilai > 0.
- [ ] **Step 2:** `pytest scripts/tests/test_business_queries.py` → FAIL.
- [ ] **Step 3: Implementasi.** Aging per spec: `SUM(stock_on_hand) / NULLIF(SUM(qty_out), 0)` dari snapshot. BQ9 menghitung `COUNT(DISTINCT transfer_id)` per bulan. Jenis grafik mengikuti slide: bar (BQ1, BQ7, BQ9), pie (BQ2), heatmap (BQ3, BQ5, BQ6), grouped bar (BQ4), horizontal bar (BQ8). Matplotlib dengan DPI 200.
- [ ] **Step 4:** `pytest` → PASS. Cek setiap grafik dengan membukanya (Read PNG).
- [ ] **Step 5:** Commit `feat: business queries and charts`.

### Task 6: Pembanding ETL manual Tugas I

**Files:**
- Create: `scripts/etl_manual_tugas1.py`, `scripts/compare_tugas1_vs_dbt.py`
- Test: `scripts/tests/test_compare.py`

**Interfaces:**
- Produces: `etl_manual_tugas1.py` membangun `inventory_tugas1.duckdb` dengan DDL + INSERT manual, urutan ditulis tangan, dan pengecekan kualitas `assert` di Python. `compare_tugas1_vs_dbt.py` mencetak tabel `objek | baris_tugas1 | baris_dbt | status` dan baris `KESIMPULAN`. Opsi `--naive` mereplikasi kesalahan khas, yaitu join ke dimensi **tanpa dedup** (memakai tabel sumber mentah), sehingga hasilnya BERBEDA.

- [ ] **Step 1: Test.** Mode normal → semua `IDENTIK`. Mode `--naive` → BQ8 berbeda dan jumlah baris fakta > 10.000 (efek duplikat produk).
- [ ] **Step 2:** `pytest scripts/tests/test_compare.py` → FAIL.
- [ ] **Step 3:** Implementasi. Perbandingan dilakukan per baris pada nilai natural (`transaction_id`, `product_id`, `warehouse_id`, tanggal, quantity), per dimensi, dan per BQ (memakai SQL BQ yang sama, dengan referensi tabel diganti).
- [ ] **Step 4:** `pytest` → PASS. Simpan keluaran kedua mode ke `logs/compare_normal.txt` dan `logs/compare_naive.txt`, serta catat waktu eksekusi ETL manual vs `dbt build`.
- [ ] **Step 5:** Commit `feat: Tugas I manual ETL comparison`.

### Task 7: Target PostgreSQL dan notebook Colab

**Files:**
- Create: `inventory_dbt/notebooks/inventory_dbt_colab.ipynb`
- Test: `scripts/tests/test_portability.py`

- [ ] **Step 1: Test.** (a) `dbt compile --profiles-dir . --target postgres` dengan env var dummy (`NEON_HOST=localhost` dst.) **harus berhasil tanpa koneksi**. Jika dbt-postgres memerlukan koneksi untuk compile, uji dengan `dbt parse --target postgres` dan catat batasan ini. (b) Grep SQL di `models/` dan `analyses/` tidak memuat fungsi khusus DuckDB (`strftime`, `generate_series`, `//`, `list_`, `epoch_ms`). (c) Notebook valid menurut `nbformat.validate` dan setiap sel kode lolos `ast.parse` setelah baris `!`/`%` dibuang.
- [ ] **Step 2:** Jalankan test → FAIL.
- [ ] **Step 3: Implementasi.** Perbaiki SQL bila ada yang tidak portabel. Isi notebook:
  1. pasang versi terkunci;
  2. mount Drive atau unggah zip;
  3. set env Neon via `getpass` / Colab Secrets (tanpa hardcode);
  4. `generate_source_data.py`, lalu `load_source.py --target postgres` (tambahkan dukungan `psycopg2` di `load_source.py` dengan argumen `--target {duckdb,postgres}`);
  5. `dbt debug`, `dbt build --target postgres`;
  6. BQ dan grafik.

  Setiap sel diberi markdown penjelasan untuk orang awam.
- [ ] **Step 4:** Test → PASS.
- [ ] **Step 5:** Commit `feat: postgres portability and Colab notebook`.

### Task 8: Elaborasi ClassicModels

**Files:**
- Create: `classicmodels_dbt/` (struktur mengikuti `activity.html`), `classicmodels_dbt/explore_source.py` (salin dari `explore_source.py/explore_source.py`), `classicmodels_dbt/logs/*.txt`

- [ ] **Step 1:** Baca `activity.html/activity.html` sepenuhnya. Catat langkah, nama model, dan pertanyaan/tugas yang harus dikerjakan mahasiswa ke `classicmodels_dbt/ACTIVITY_NOTES.md`.
- [ ] **Step 2:** Siapkan `classicmodels.duckdb`. Utamakan data asli dari MySQL Tutorial (unduh `mysqlsampledatabase.zip`, konversi INSERT MySQL ke DuckDB lewat skrip). Bila gagal, gunakan sampel berskema identik dan catat di NOTES.
- [ ] **Step 3:** `python explore_source.py` → output `[OK] All 8 expected tables found.` Simpan ke log.
- [ ] **Step 4:** Implementasikan model sesuai activity, lalu `dbt build --profiles-dir .` → semua PASS. Simpan log, jawab pertanyaan activity di NOTES, dan ambil satu tabel hasil (mis. kinerja sales rep) ke `results/`.
- [ ] **Step 5:** Commit `feat: ClassicModels lab elaboration`.

### Task 9: TinyTeX dan kerangka LaTeX yang terkompilasi

**Files:**
- Modify: `Tugas II DWIB/Laporan Mahasiswa DWIB/Makalah.tex`, `references.bib`
- Create: `contents/Pendahuluan.tex`, `contents/Lampiran.tex`, `build.ps1` (pdflatex → bibtex → makeindex → pdflatex ×2)

- [ ] **Step 1:** Pasang TinyTeX (installer resmi untuk Windows ke `%APPDATA%\TinyTeX`). Pasang paket yang dibutuhkan `kultem.sty` dan `Makalah.tex` via `tlmgr` (iteratif dari pesan galat).
- [ ] **Step 2:** Ubah `Makalah.tex`:
  - judul *Modul Penyiapan Lingkungan dan Studi Kasus Data Mart Inventory*, anggota kelompok;
  - `\usepackage[bahasa]{babel}` bila tersedia (bila tidak, tetap `english` dan nama-nama sudah di-renew);
  - pasang `listings` untuk SQL/YAML/bash dengan style warna template;
  - kotak `tips`, `perhatian`, `cekberhasil`, `info` (tcolorbox);
  - `\include` Pendahuluan di frontmatter, Lampiran dan `\bibliography{references}` di backmatter;
  - `\listoffigures`, `\listoftables`.
- [ ] **Step 3:** Ganti `references.bib` dengan rujukan:
  - dbt Labs docs;
  - Handy 2017 (What exactly is dbt);
  - Shamimw (Medium);
  - Hirazone (Medium);
  - Kimball Group techniques;
  - Kimball & Ross 2013;
  - MySQL Tutorial sample DB;
  - dbt-duckdb;
  - dbt-postgres;
  - Neon;
  - Google Colab;
  - activity.html (Tim Pengampu).
- [ ] **Step 4:** `.\build.ps1` → `Makalah.pdf` terbentuk, log tanpa `! LaTeX Error` / `Undefined control sequence`.
- [ ] **Step 5:** Commit `docs: LaTeX skeleton compiles`.

### Task 10: Bab 2 — Penyiapan Lingkungan DBT

**Files:** Modify `contents/Bab2.tex`

- [ ] **Step 1:** Tulis section mengikuti spec §6 Bab 2:
  - DBT Core vs DBT Cloud (tabel dan alasan pilihan kelompok);
  - Instalasi Package: istilah, Opsi A Colab + Neon (langkah per sel notebook Task 7, cara membuat akun dan database Neon, Colab Secrets), Opsi B lokal Windows (Python, venv, pip versi terkunci, `dbt --version` dari `logs/dbt_version.txt`, `dbt debug`);
  - `profiles.yml` dua target;
  - tabel galat umum (termasuk rc version, execution policy, `dbt init` interaktif di Colab, path berspasi, `Could not find profile`, env var kosong);
  - latihan proyek pertama dari nol, yang **dijalankan sungguhan** di folder sementara (seed `gudang.csv` → model → 2 test → contoh test FAIL), dengan log dikutip apa adanya;
  - Workflow dan Use Case (tabel perintah, lineage `charts/lineage.png`, `dbt docs`).

  Setiap langkah diberi kotak *Cek keberhasilan*.
- [ ] **Step 2:** Build PDF → bebas galat; periksa visual halaman Bab 2 (render 3 halaman ke PNG dan Read).
- [ ] **Step 3:** Commit `docs: Bab 2`.

### Task 11: Bab 3 — Studi Kasus Inventory

**Files:** Modify `contents/Bab3.tex`; salin `charts/*.png` → `figures/`

- [ ] **Step 1:** Tulis:
  - Skema Data Base & Data Warehouse: tabel sumber dan karakteristik dari `logs/generate_load.txt`, star schema kedua fakta, bus matrix, SCD 1/dedup, penjelasan additive vs semi-additive, catatan bahwa angka berbeda dari slide karena data dibangkitkan ulang;
  - Skenario dan Penyelesaian: BQ1–9 sebagai skenario, langkah dbt (potongan kode model nyata), keluaran `dbt build`, tabel ringkasan test, mutation test;
  - setiap BQ dengan potongan SQL, grafik, **tabel angka dari `results/*.csv`**, dan interpretasi;
  - Tugas I vs dbt (tabel pemetaan, keluaran compare normal vs naive, penjelasan penyebab perbedaan di slide);
  - pengalaman khusus, latihan mandiri, kesimpulan, matriks peran.
- [ ] **Step 2:** Verifikasi angka. Skrip kecil `scripts/check_numbers.py` mengekstrak setiap angka berformat Indonesia di Bab3 yang ditandai `% src: results/xxx.csv`, lalu mencocokkannya dengan CSV → semua cocok.
- [ ] **Step 3:** Build PDF bebas galat dan periksa visual.
- [ ] **Step 4:** Commit `docs: Bab 3`.

### Task 12: Bab 1 — DBT sebagai Tools Bantu Data Warehouse

**Files:** Modify `contents/Bab1.tex`

- [ ] **Step 1:** Tulis:
  - Pengenalan DBT: konsep dan arsitektur (ELT, diagram TikZ, tabel konsep), fitur dan dukungan, keuntungan dan batasan, dengan sitasi Handy/Shamimw/Hirazone/dbt docs;
  - Model dalam DBT: materialisasi (tabel perbandingan), dasar Kimball 4 langkah dan tabel teknik beserta lokasinya di modul;
  - Classic Model: hasil Task 8 dengan log nyata dan satu tabel hasil;
  - Struktur Model (layer, struktur direktori `inventory_dbt`, `dbt_project.yml`);
  - Data Quality (generic vs singular, contoh dari proyek).
- [ ] **Step 2:** Build PDF bebas galat dan periksa visual.
- [ ] **Step 3:** Commit `docs: Bab 1`.

### Task 13: Pendahuluan, Lampiran, verifikasi akhir

**Files:** Modify `contents/Pendahuluan.tex`, `contents/Lampiran.tex`; Create `DWBI_Kelompok_Inventory.zip` (proyek + modul tanpa `.venv`, `*.duckdb`, `target/`)

- [ ] **Step 1:** Pendahuluan:
  - tujuan, sasaran pembaca, prasyarat;
  - peta modul dengan estimasi waktu (TikZ);
  - konvensi kotak;
  - isi lampiran zip;
  - tabel peran anggota;
  - status verifikasi (versi dari `requirements.txt`, tanggal uji, ringkasan PASS).

  Lampiran: ringkasan perintah, checklist praktik, glosarium.
- [ ] **Step 2: Verifikasi akhir.**
  - `grep -n "TBD\|TODO\|xxx\|Mahasiswa 1\|lipsum"` di `contents/` → kosong.
  - Nama ketiga anggota muncul di Pendahuluan, `mybox` setiap Bab, dan matriks peran.
  - Jalankan ulang seluruh pipeline dari nol: hapus `*.duckdb` dan `target/`, lalu generate → load → `dbt build` → BQ → compare → `pytest`, semua PASS dan CSV identik.
  - Build PDF final tanpa galat atau referensi `??`.
- [ ] **Step 3:** Buat zip, lalu commit `docs: final module`.
