{#- date_key(kolom): ubah tanggal/timestamp menjadi smart key integer YYYYMMDD.
    Memakai EXTRACT sehingga sama persis di DuckDB maupun PostgreSQL. -#}
{% macro date_key(column_name) -%}
    cast(extract(year from {{ column_name }}) * 10000
         + extract(month from {{ column_name }}) * 100
         + extract(day from {{ column_name }}) as integer)
{%- endmacro %}
