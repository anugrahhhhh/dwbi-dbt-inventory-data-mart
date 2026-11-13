"""Menjalankan 4 business query Step 5 activity.html dan menyimpan hasilnya ke results/."""
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
QUERIES = {
    "revenue_by_product_line": """
        SELECT p.product_line, SUM(f.revenue) AS total_revenue, SUM(f.gross_profit) AS total_gross_profit,
               COUNT(DISTINCT f.order_id) AS order_count,
               ROUND(SUM(f.gross_profit) / NULLIF(SUM(f.revenue),0) * 100, 1) AS gross_margin_pct
        FROM fct_order_lines f JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.product_line ORDER BY total_revenue DESC""",
    "top5_customers_payments": """
        SELECT c.customer_name, c.country, SUM(fp.amount) AS total_paid, COUNT(*) AS payment_count
        FROM fct_payments fp JOIN dim_customer c ON fp.customer_key = c.customer_key
        GROUP BY c.customer_name, c.country ORDER BY total_paid DESC LIMIT 5""",
    "top5_sales_reps_2004": """
        SELECT e.full_name, e.job_title, o.territory, SUM(sp.total_revenue) AS ytd_revenue,
               SUM(sp.order_count) AS total_orders, SUM(sp.unique_customers) AS customers_served
        FROM fct_sales_performance sp
        JOIN dim_employee e ON sp.sales_rep_key = e.employee_key
        JOIN dim_office o ON sp.office_key = o.office_key
        WHERE sp.year = 2004 GROUP BY e.full_name, e.job_title, o.territory
        ORDER BY ytd_revenue DESC LIMIT 5""",
    "monthly_revenue": """
        SELECT dd.year, dd.month, dd.month_name, SUM(f.revenue) AS monthly_revenue
        FROM fct_order_lines f JOIN dim_date dd ON f.order_date_id = dd.date_id
        GROUP BY dd.year, dd.month, dd.month_name ORDER BY dd.year, dd.month""",
    "checkpoints": """
        SELECT (SELECT MIN(date_id) FROM dim_date) AS min_date, (SELECT MAX(date_id) FROM dim_date) AS max_date,
               (SELECT COUNT(*) FROM dim_date) AS total_days,
               (SELECT SUM(revenue) FROM fct_order_lines) AS total_revenue_all_time,
               (SELECT COUNT(*) FROM fct_order_lines) AS order_lines,
               (SELECT COUNT(*) FROM fct_payments) AS payments,
               (SELECT COUNT(*) FROM fct_sales_performance) AS rep_months""",
}
con = duckdb.connect(str(HERE / "classicmodels.duckdb"), read_only=True)
for name, sql in QUERIES.items():
    df = con.execute(sql).df()
    df.to_csv(HERE / "results" / f"{name}.csv", index=False)
    print(f"\n== {name} ==\n{df.head(12).to_string(index=False)}")
