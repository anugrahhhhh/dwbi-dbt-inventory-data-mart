# build.ps1 — kompilasi modul menjadi Makalah.pdf (TinyTeX / MiKTeX / TeX Live)
# Pemakaian: buka PowerShell di folder ini, lalu jalankan  .\build.ps1
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
if (Test-Path "$env:APPDATA\TinyTeX\bin\windows") { $env:Path = "$env:APPDATA\TinyTeX\bin\windows;" + $env:Path }

$py = Join-Path $PSScriptRoot "..\..\.venv\Scripts\python.exe"
if (Test-Path $py) { & $py sync_assets.py }

pdflatex -interaction=nonstopmode -halt-on-error Makalah.tex | Out-Null
bibtex Makalah *> $null
makeindex -q Makalah.idx *> $null
pdflatex -interaction=nonstopmode -halt-on-error Makalah.tex | Out-Null
pdflatex -interaction=nonstopmode -halt-on-error Makalah.tex | Out-Null

$errors = Select-String -Path Makalah.log -Pattern '^! ' | ForEach-Object { $_.Line }
$undef  = Select-String -Path Makalah.log -Pattern 'undefined' | Where-Object { $_.Line -notmatch 'Font' } | ForEach-Object { $_.Line }
if ($errors) { "GALAT LaTeX:"; $errors; exit 1 }
if ($undef)  { "Peringatan referensi/sitasi belum terdefinisi:"; $undef | Select-Object -First 10 }
"Makalah.pdf selesai dibuat."
