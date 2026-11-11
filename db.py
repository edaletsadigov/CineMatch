
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text, URL


# ==========================================
# Database Configuration
# ==========================================

DB_SERVER = "localhost"
DB_PORT = 5432
DB_NAME = "cinematch"
DB_USER = "cinematch"
DB_PASSWORD = "Cinematch1234!"


# ==========================================
# Project Paths
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent
BASE_SQL_FILE = PROJECT_ROOT / "base.sql"


# ==========================================
# Database Connection
# ==========================================

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


# ==========================================
# SQL File Execution
# ==========================================

def run_sql_file(path, engine):
    """Execute semicolon-separated SQL statements."""

    sql = Path(path).read_text(encoding="utf-8")

    statements = [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


# ==========================================
# Database Setup
# ==========================================

def setup_database():
    """Initialize PostgreSQL database and required schemas."""

    engine = get_engine()

    try:
        # PostgreSQL connection test
        with engine.connect() as conn:
            version = conn.execute(
                text("SELECT version()")
            ).scalar()

            print("PostgreSQL version:", version[:80])

        # Enable pgvector extension
        with engine.begin() as conn:
            conn.execute(
                text("CREATE EXTENSION IF NOT EXISTS vector")
            )

        # Create Bronze, Silver and Gold schemas
        run_sql_file(BASE_SQL_FILE, engine)

        print("Database:", DB_NAME)
        print("Connected as:", DB_USER)

        # Verify pgvector extension
        with engine.connect() as conn:
            extension = conn.execute(
                text("""
                    SELECT extname
                    FROM pg_extension
                    WHERE extname = 'vector'
                """)
            ).scalar()

            print("pgvector extension:", extension)

        # Verify schemas
        query = """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name IN ('bronze', 'silver', 'gold')
            ORDER BY schema_name
        """

        with engine.connect() as conn:
            schemas = pd.read_sql(
                text(query),
                conn,
            )

        print("\nDatabase schemas:")
        print(schemas)

    finally:
        engine.dispose()


# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    setup_database()
