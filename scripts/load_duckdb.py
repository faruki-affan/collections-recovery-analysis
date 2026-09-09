from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
db_path = ROOT / "data" / "warehouse" / "collections.duckdb"
db_path.parent.mkdir(parents=True, exist_ok=True)
golden = ROOT / "data" / "golden"
clean = ROOT / "data" / "clean"

con = duckdb.connect(str(db_path))
con.execute("CREATE SCHEMA IF NOT EXISTS staging")
con.execute("CREATE SCHEMA IF NOT EXISTS clean")
con.execute("CREATE SCHEMA IF NOT EXISTS golden")
con.execute("CREATE SCHEMA IF NOT EXISTS metrics")
con.execute("CREATE SCHEMA IF NOT EXISTS analysis")

for folder, schema in [(golden, "golden"), (clean, "clean")]:
    if not folder.exists():
        continue
    for p in folder.glob("*.parquet"):
        con.execute(
            f"CREATE OR REPLACE TABLE {schema}.{p.stem} AS SELECT * FROM read_parquet(?)",
            [str(p)],
        )
        print(f"loaded {schema}.{p.stem}")

con.execute(
    "CREATE OR REPLACE VIEW golden.account_month AS SELECT * FROM golden.golden_account_month"
)

sql_root = ROOT / "sql"
for rel in [
    "metrics/01_core_metrics.sql",
    "metrics/02_funnel.sql",
    "analysis/01_monthly_and_mix.sql",
    "analysis/02_drivers.sql",
]:
    text = (sql_root / rel).read_text(encoding="utf-8")
    # Skip files that assume staging.payments if using parquet-only load
    try:
        con.execute(text)
        print("applied", rel)
    except Exception as e:
        print("skip/warn", rel, e)

print("warehouse", db_path)
con.close()
