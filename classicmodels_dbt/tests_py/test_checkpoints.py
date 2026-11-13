"""Checkpoint dari lembar kegiatan activity.html, dijadikan test otomatis."""
from pathlib import Path

import duckdb
import pytest

DB = Path(__file__).resolve().parents[1] / "classicmodels.duckdb"


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


def q(con, sql):
    return con.execute(sql).fetchall()


def test_eight_source_tables(con):
    names = {r[0] for r in q(con, "select table_name from information_schema.tables "
                                  "where table_schema='main' and table_type='BASE TABLE'")}
    assert {"customers", "employees", "offices", "orderdetails", "orders",
            "payments", "productlines", "products"} <= names


def test_sixteen_models(con):
    rows = q(con, "select table_name from information_schema.tables where table_schema='main' "
                  "and (table_name like 'stg_%' or table_name like 'dim_%' or table_name like 'fct_%')")
    assert len(rows) == 16


def test_dim_date_range(con):
    assert q(con, "select min(date_id), max(date_id), count(*) from dim_date")[0] == \
        (__import__("datetime").date(2003, 1, 1), __import__("datetime").date(2006, 12, 31), 1461)


def test_dim_employee_manager_resolved(con):
    # semua pegawai kecuali presiden memiliki nama manajer
    assert q(con, "select count(*) from dim_employee where manager_full_name is null")[0][0] == 1


def test_classic_cars_highest_revenue(con):
    top = q(con, "select p.product_line from fct_order_lines f join dim_product p using (product_key) "
                 "group by 1 order by sum(f.revenue) desc limit 1")[0][0]
    assert top == "Classic Cars"


def test_total_revenue_about_9_6_million(con):
    total = q(con, "select sum(revenue) from fct_order_lines")[0][0]
    assert 9.5e6 <= float(total) <= 9.7e6


def test_top5_reps_2004_include_emea_or_apac(con):
    terr = {r[0] for r in q(con, """
        select o.territory from fct_sales_performance sp
        join dim_employee e on sp.sales_rep_key = e.employee_key
        join dim_office o on sp.office_key = o.office_key
        where sp.year = 2004 group by e.full_name, o.territory
        order by sum(sp.total_revenue) desc limit 5""")}
    assert terr & {"EMEA", "APAC"}


def test_order_lines_complete(con):
    assert q(con, "select (select count(*) from orderdetails) = (select count(*) from fct_order_lines)")[0][0]
