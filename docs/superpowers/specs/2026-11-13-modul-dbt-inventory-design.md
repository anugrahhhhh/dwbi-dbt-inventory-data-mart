# Spec: Modul dbt Tugas II DWBI — Studi Kasus Data Mart Inventory

Tanggal: 2026-11-13 · Tenggat modul: 2026-11-16 · Kelompok: Vytis Rabbani Rex, Muhammad Raihan Sinergie Proton, Alfat Raehan

## 1. Tujuan dan kriteria sukses

Menghasilkan **modul LaTeX** (template `Makalah.tex` + `contents/Bab1–3.tex`, kelas `kultem`) yang:

1. dapat diikuti orang awam untuk menyiapkan lingkungan dbt **di Google Colab dan di komputer lokal**;
2. mendokumentasikan studi kasus **Data Mart Inventory** (kasus Tugas I) yang dibangun dengan dbt;
3. memuat elaborasi **ClassicModels** sesuai `activity.html`;
4. menuliskan **peran setiap anggota**;
5. berkompilasi menjadi PDF tanpa galat.

Bobot penilaian yang dikejar: kelengkapan 30%, kejelasan 35%, bahasa 15%, correctness 20%.

**Aturan correctness:** setiap potongan kode, keluaran terminal, dan angka di modul berasal dari eksekusi nyata proyek yang disertakan. Tidak ada angka karangan.

## 2. Keputusan yang sudah disepakati

| Keputusan | Pilihan |
|---|---|
| Sumber kode/angka | File proyek asli kelompok tidak tersedia → proyek **dibangun ulang dari desain di slide** (`DBT Presentation Slides.pdf`) dengan data sintetis berkarakteristik sama. Angka akan berbeda dari slide. |
| Fakta tambahan | **Ya**: `fact_inventory_daily_snapshot` (periodic snapshot, semi-additive). |
| Kompilasi LaTeX | Pasang **TinyTeX** lokal untuk verifikasi; berkas tetap kompatibel Overleaf. |
| Peran anggota | Vytis = Data Modeler; Raihan = dbt & Pipeline Engineer; Alfat = Documentation & QA Lead. |
| Kredensial | Tidak ada password di modul; `profiles.yml` memakai `env_var()`. |

## 3. Struktur berkas yang dihasilkan

```
alfat dtwh/
├── inventory_dbt/                  # proyek dbt studi kasus
│   ├── dbt_project.yml
│   ├── profiles.yml                # target duckdb (lokal) + postgres (Colab/Neon, env_var)
│   ├── macros/                     # mis. date_key()
│   ├── models/
│   │   ├── sources.yml
│   │   ├── staging/                # stg_products, stg_warehouses, stg_inventory_movements (+ schema.yml)
│   │   └── marts/                  # dim_date, dim_product, dim_warehouse, dim_movement_type,
│   │                               # fact_inventory, fact_inventory_daily_snapshot (+ schema.yml)
│   ├── tests/                      # singular tests
│   ├── analyses/                   # bq1..bq9 *.sql
│   ├── scripts/
│   │   ├── generate_source_data.py # bangkitkan 3 tabel sumber (seed tetap)
│   │   ├── load_source.py          # muat CSV → DuckDB / PostgreSQL
│   │   ├── run_business_queries.py # jalankan analyses terkompilasi → results/*.csv + charts/*.png
│   │   ├── etl_manual_tugas1.py    # pembanding gaya Tugas I (SQL/pandas manual)
│   │   └── compare_tugas1_vs_dbt.py
│   ├── data/                       # CSV sumber
│   ├── results/  charts/
│   └── notebooks/inventory_dbt_colab.ipynb   # jalur Colab + Neon
├── classicmodels_dbt/              # elaborasi activity.html (dbt-duckdb)
└── Tugas II DWIB/Laporan Mahasiswa DWIB/     # modul LaTeX (diisi di tempat)
    ├── Makalah.tex, contents/Bab1.tex, Bab2.tex, Bab3.tex, contents/Pendahuluan.tex, contents/Lampiran.tex
    ├── figures/ (diagram, grafik BQ, lineage)
    └── references.bib (diganti rujukan dbt/Kimball)
```

## 4. Proyek `inventory_dbt`

### 4.1 Data sumber (meniru slide 15)

| Tabel | Baris | Karakteristik |
|---|---|---|
| `source_products` | 50 | 10 `product_id` unik; 40 baris duplikat versi lama dengan `updated_at` berbeda (beberapa berisi spasi berlebih / string kosong). 8 kategori: Air Fryer, Blender, Coffee Maker, Electric Kettle, Electric Stove, Hand Mixer, Microwave, Rice Cooker (Blender dan Rice Cooker masing-masing 2 produk). |
| `source_warehouses` | 15 | 3 `warehouse_id` unik (Warehouse Jawa, Sumatra, Kalimantan); 12 duplikat versi lama. |
| `source_inventory_movements` | 10.000 | Periode 2024-01-01 s.d. 2025-12-31; 6 tipe: PURCHASE, SALE, TRANSFER, LOST, DAMAGED, FOUND, dengan proporsi mendekati slide (TRANSFER ±33%, FOUND ±0,3%). Setiap `transfer_id` menghasilkan tepat 2 baris (keluar dari gudang asal, masuk ke gudang tujuan). |

Generator memakai seed tetap dan menjamin stok tidak pernah negatif (SALE/LOST/DAMAGED/TRANSFER-keluar hanya dibuat bila stok cukup). Kolom arah transfer: `transfer_direction` ∈ {OUT, IN, NULL}.

### 4.2 Model

| Lapisan | Model | Materialization | Isi |
|---|---|---|---|
| Staging | `stg_products`, `stg_warehouses`, `stg_inventory_movements` | view | TRIM, NULLIF(''), cast `quantity` BIGINT, normalisasi huruf `movement_type` |
| Dimensi | `dim_product`, `dim_warehouse` | table | SCD Type 1: dedup `ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC)`, surrogate key |
| Dimensi | `dim_movement_type` | table | tipe + `direction_sign` (+1/−1/0 untuk TRANSFER yang ditentukan sisi) + `movement_group` (inbound/outbound/adjustment) |
| Dimensi | `dim_date` | table | kalender penuh 2024-01-01..2025-12-31, smart key YYYYMMDD |
| Fakta | `fact_inventory` | table | grain 1 baris = 1 movement; FK ke 4 dimensi; DD `transaction_id`, `transfer_id`; measure `quantity` (additive, selalu positif) dan `signed_quantity` (additive, + masuk / − keluar) |
| Fakta | `fact_inventory_daily_snapshot` | table | grain 1 baris = produk × gudang × hari; `stock_on_hand` (**semi-additive**: boleh dijumlah lintas produk/gudang, tidak lintas waktu), `qty_in`, `qty_out` (additive). Dibentuk dari `fact_inventory` (fact-on-fact). |

SQL ditulis **portabel PostgreSQL ↔ DuckDB** (hindari fungsi khusus dialek; perbedaan yang tak terhindarkan dibungkus macro dengan `adapter.dispatch`). Versi dikunci: dbt-core stabil terbaru yang didukung bersama oleh dbt-duckdb dan dbt-postgres (ditetapkan saat implementasi, bukan versi rc).

### 4.3 Test

- Generic: `unique` + `not_null` semua surrogate key; `not_null` + `relationships` **untuk keempat FK** `fact_inventory` dan FK snapshot; `accepted_values` movement type dan transfer direction; source tests (keunikan `transaction_id`).
- Singular: (a) jumlah baris `fact_inventory` = sumber; (b) setiap `transfer_id` punya tepat 1 OUT dan 1 IN dengan quantity sama; (c) `stock_on_hand` ≥ 0; (d) stok akhir snapshot = Σ `signed_quantity` fakta (rekonsiliasi antarfakta); (e) dedup dimensi: jumlah baris = jumlah ID unik sumber.
- Mutation test: data sengaja dirusak (transfer tanpa pasangan, stok negatif), lalu ditunjukkan test FAIL.

### 4.4 Business queries (`analyses/`, mengikuti slide 20–28)

| BQ | Pertanyaan | Sumber |
|---|---|---|
| BQ1 | Rata-rata inventory aging per gudang | snapshot |
| BQ2 | Distribusi aktivitas inventory (proporsi per tipe) | fact_inventory |
| BQ3 | Heatmap aktivitas: gudang × tipe | fact_inventory |
| BQ4 | Aktivitas per gudang (grouped bar) | fact_inventory |
| BQ5 | Aging per kategori produk × gudang | snapshot |
| BQ6 | Unit hilang dan rusak per kategori × gudang | fact_inventory |
| BQ7 | Total aktivitas per tipe | fact_inventory |
| BQ8 | Total unit terjual per kategori | fact_inventory |
| BQ9 | Jumlah transaksi transfer per bulan | fact_inventory + dim_date |

**Definisi aging (ditulis eksplisit di modul):** *days of inventory*, yaitu berapa hari rata-rata sebuah unit tertahan di gudang. Untuk setiap kelompok (gudang, atau kategori × gudang): `aging_days = Σ stock_on_hand harian / Σ qty_out` dari `fact_inventory_daily_snapshot`, dengan `qty_out` = SALE + LOST + DAMAGED + TRANSFER-keluar. Rumus ini dipilih karena mudah dijelaskan ke orang awam dan langsung memperlihatkan kegunaan periodic snapshot.

### 4.5 Pembanding Tugas I

`etl_manual_tugas1.py` membangun data mart yang sama dengan SQL manual (DDL + INSERT, urutan ditulis tangan). `compare_tugas1_vs_dbt.py` membandingkan per baris dan per BQ. Modul menjelaskan bahwa slide melaporkan hasil yang **berbeda**; penyebab umum (filter, agregasi, grain, duplikat dimensi) ditunjukkan dengan **contoh nyata**: menjalankan BQ tanpa dedup dimensi menghasilkan angka berbeda, dan setelah definisi diseragamkan hasilnya identik.

## 5. Elaborasi ClassicModels

Mengikuti `activity.html`: muat data ClassicModels ke DuckDB, jalankan `explore_source.py`, bangun staging → dimensi → fakta sesuai lembar kegiatan, `dbt build`, catat jumlah model/test dan satu tabel hasil. Data dari MySQL Tutorial sample database; bila tidak bisa diunduh, dibuat sampel dengan skema identik dan hal itu dinyatakan di modul.

## 6. Isi modul LaTeX

- **Pendahuluan:** tujuan, sasaran pembaca dan prasyarat, peta modul dengan estimasi waktu, konvensi (kotak Tips / Perhatian / Cek keberhasilan / Info via `tcolorbox`), isi lampiran, tabel peran anggota, status verifikasi (versi Python/dbt dan tanggal uji).
- **Bab 1** (template): Pengenalan DBT (konsep dan arsitektur, ELT vs ETL, fitur dan dukungan, keuntungan dan batasan); Model dalam DBT (materialisasi, dasar Kimball, teknik yang dipakai, Classic Model, struktur model/layer); Data Quality dalam DBT.
- **Bab 2** (template): DBT Core vs DBT Cloud; Instalasi Package: istilah, **Opsi A Google Colab + Neon PostgreSQL**, **Opsi B lokal Windows (Python venv + DuckDB)**, `profiles.yml`, tabel galat umum (termasuk jebakan versi rc, PowerShell execution policy, `dbt init` di Colab), latihan proyek pertama dari nol (seed → model → test, termasuk contoh test FAIL); Workflow dan Use Case: tabel perintah, lineage, docs.
- **Bab 3** (template): Skema Data Base & Data Warehouse (OLTP, star schema kedua fakta, bus matrix, SCD 1 / dedup, semi-additive); Skenario dan Penyelesaian (BQ1–9, langkah dbt, hasil test, hasil BQ dengan tabel dan grafik, Tugas I vs dbt, pengalaman khusus, latihan mandiri, kesimpulan, matriks peran).
- **Lampiran:** ringkasan perintah, checklist praktik, glosarium. **Daftar Pustaka** memakai natbib dari `references.bib`.
- Peran anggota muncul di Pendahuluan, `mybox` awal setiap bab, dan matriks peran Bab 3.
- Diagram (star schema, lineage, alur ELT) digambar dengan TikZ atau dibangkitkan Python ke PNG.

## 7. Verifikasi

1. `dbt build` pada target DuckDB: seluruh model dan test PASS; log disalin ke modul.
2. Model diuji kompilasi untuk target postgres (`dbt compile --target postgres`, atau dijalankan bila PostgreSQL tersedia). Bila tidak bisa dijalankan pada Postgres sungguhan, modul menyatakan bahwa jalur Colab + Neon mengikuti konfigurasi kelompok di slide dan hanya dikompilasi.
3. Notebook Colab dibuat dan diperiksa sintaksnya (tidak dapat dijalankan dari laptop ini).
4. LaTeX dikompilasi dengan TinyTeX tanpa galat; daftar isi, gambar, tabel, dan rujukan terisi.

## 8. Di luar lingkup

Slide baru (PPT kelompok sudah ada); dbt Cloud hands-on; incremental model dan snapshot dbt (hanya dijelaskan konsepnya).

## 9. Risiko

- Angka berbeda dari slide → dinyatakan jelas di modul; mudah diganti bila file asli dikirim.
- Kompatibilitas `kultem.sty` dengan TinyTeX → paket yang hilang dipasang via `tlmgr`.
- Waktu (3 hari) → urutan kerja: proyek inventory → ClassicModels → LaTeX Bab 2 → Bab 3 → Bab 1 → Pendahuluan dan Lampiran.
