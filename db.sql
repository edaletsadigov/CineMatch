from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text, URL

DB_SERVER = "localhost"
DB_PORT = 5432
DB_NAME = "cinematch"
DB_USER = "cinematch"
DB_PASSWORD = "Cinematch1234!"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"

def get_engine(database=DB_NAME):
    url = URL.create(
        "postgresql+psycopg",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_SERVER,
        port=DB_PORT,
        database=database,
    )

    return create_engine(url)


def run_sql_file(path, engine):
    """Run a .sql file."""
    sql = Path(path).read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(sql))


def setup_database():
    """One-time database setup."""

    engine = get_engine()

    with engine.begin() as conn:
        print(
            "PostgreSQL version:",
            conn.execute(text("SELECT version()")).scalar()[:80],
        )
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS silver"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))
    print("Database:", DB_NAME)
    print("Connected as:", DB_USER)

    with engine.connect() as conn:
        schemas = pd.read_sql(
            text("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN ('bronze', 'silver', 'gold')
                ORDER BY schema_name
            """),
            conn,
        )

        print(schemas)


if __name__ == "__main__":
    setup_database()