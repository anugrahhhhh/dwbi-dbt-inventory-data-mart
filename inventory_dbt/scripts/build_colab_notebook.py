"""
build_colab_notebook.py
Menyusun notebooks/inventory_dbt_colab.ipynb: panduan langkah demi langkah menjalankan
proyek inventory_dbt di Google Colab dengan basis data PostgreSQL Neon.
"""
from pathlib import Path

import nbformat as nbf

PROJECT_DIR = Path(__file__).resolve().parents[1]

CELLS = [
    ("md", """# Data Mart Inventory dengan dbt — Google Colab + Neon PostgreSQL
Notebook ini menjalankan proyek `inventory_dbt` sepenuhnya di peramban (tanpa instalasi di komputer).
Jalankan sel **berurutan dari atas** dengan menekan `Shift+Enter`.

* Tanda `!` di awal baris = perintah terminal. Tanda `%cd` = pindah folder.
* Yang perlu disiapkan: akun Google, akun Neon (gratis), dan berkas `inventory_dbt.zip`."""),
    ("md", """## Langkah 1 — Hubungkan Google Drive
Berkas di Colab hilang ketika *runtime* direset, maka proyek disimpan di Google Drive.
Unggah `inventory_dbt.zip` ke folder **My Drive** terlebih dahulu. Jendela izin akun Google akan muncul."""),
    ("code", """from google.colab import drive
drive.mount('/content/drive')
%cd /content/drive/MyDrive"""),
    ("md", """## Langkah 2 — Pasang dbt dengan versi terkunci
Versi dikunci agar `dbt-core` cocok dengan adapter. **Jangan** memakai `pip install dbt-postgres` tanpa versi:
pip dapat memasang versi *release candidate* (mis. `1.13.0-rc1`) yang belum stabil."""),
    ("code", """!pip install -q "dbt-core~=1.11.0" "dbt-postgres~=1.11.0" "dbt-duckdb~=1.11.0" duckdb pandas matplotlib psycopg2-binary
!dbt --version"""),
    ("md", """**Cek keberhasilan:** keluaran memuat `installed: 1.11.x` dan baris `postgres: 1.11.x` di bagian *Plugins*."""),
    ("md", """## Langkah 3 — Ekstrak proyek"""),
    ("code", """!unzip -q -o inventory_dbt.zip
%cd /content/drive/MyDrive/inventory_dbt
!ls"""),
    ("md", """**Cek keberhasilan:** daftar berkas memuat `dbt_project.yml` dan `profiles.yml`."""),
    ("md", """## Langkah 4 — Simpan kredensial Neon dengan aman
1. Buat proyek di https://neon.tech, salin *connection string* (host, user, password, database).
2. Di Colab, klik ikon **kunci (Secrets)** di panel kiri, tambahkan `NEON_HOST`, `NEON_USER`,
   `NEON_PASSWORD`, `NEON_DB`, lalu aktifkan *Notebook access*.

Password **tidak pernah** ditulis di notebook maupun di `profiles.yml`; dbt membacanya dengan `env_var()`."""),
    ("code", """import os
from getpass import getpass
try:
    from google.colab import userdata
    for k in ["NEON_HOST", "NEON_USER", "NEON_PASSWORD", "NEON_DB"]:
        os.environ[k] = userdata.get(k)
except Exception:
    # cadangan bila Secrets belum diisi: ketik manual (tidak tersimpan di notebook)
    for k in ["NEON_HOST", "NEON_USER", "NEON_DB"]:
        os.environ[k] = input(k + ": ")
    os.environ["NEON_PASSWORD"] = getpass("NEON_PASSWORD: ")
print("Host:", os.environ["NEON_HOST"])"""),
    ("md", """## Langkah 5 — Extract & Load: bangkitkan dan muat data sumber
dbt tidak memindahkan data. Skrip berikut membangkitkan tiga tabel sumber lalu memuatnya ke skema `public` di Neon."""),
    ("code", """!python scripts/generate_source_data.py
!python scripts/load_source.py --target postgres"""),
    ("md", """## Langkah 6 — Uji koneksi dbt"""),
    ("code", """!dbt debug --profiles-dir . --target postgres"""),
    ("md", """**Cek keberhasilan:** baris terakhir berbunyi `All checks passed!`. Bila gagal, periksa Secrets pada Langkah 4."""),
    ("md", """## Langkah 7 — Bangun data mart dan jalankan seluruh test
`dbt build` = `dbt run` + `dbt test` dalam urutan DAG. Hasilnya dibuat di skema `analytics_dbt`."""),
    ("code", """!dbt build --profiles-dir . --target postgres"""),
    ("md", """**Cek keberhasilan:** ringkasan akhir `Done. PASS=59 WARN=0 ERROR=0`."""),
    ("md", """## Langkah 8 — Business query dan grafik"""),
    ("code", """!python scripts/run_business_queries.py --target postgres
from IPython.display import Image, display
for n in ["bq1_aging_by_warehouse", "bq8_units_sold_by_category", "bq9_transfers_per_month"]:
    display(Image(f"charts/{n}.png"))"""),
    ("md", """## Alternatif tanpa Neon — DuckDB di Colab
Bila belum memiliki akun Neon, proyek yang sama dapat dijalankan dengan DuckDB (berkas lokal di Drive):"""),
    ("code", """!python scripts/load_source.py
!dbt build --profiles-dir .
!python scripts/run_business_queries.py"""),
    ("md", """## Langkah 9 — Dokumentasi
`dbt docs serve` tidak dapat dibuka dari Colab (butuh server web lokal). Jalankan `dbt docs generate`,
lalu unduh folder `target/` dan buka `index.html` di komputer, atau gunakan dbt Cloud."""),
    ("code", """!dbt docs generate --profiles-dir . --target postgres
!ls target | head"""),
]


def build() -> Path:
    nb = nbf.v4.new_notebook()
    nb.metadata["colab"] = {"provenance": []}
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
    nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src)
                for kind, src in CELLS]
    out = PROJECT_DIR / "notebooks" / "inventory_dbt_colab.ipynb"
    out.parent.mkdir(exist_ok=True)
    nbf.write(nb, out)
    return out


if __name__ == "__main__":
    print("Notebook ditulis ke", build())
