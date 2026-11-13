
from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, URL


# ==========================================
# Project Configuration
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent
BASE_SQL_FILE = PROJECT_ROOT / "base.sql"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


# ==========================================
# Psycopg Configuration
# ==========================================

PG_BIN_DIR = os.getenv("PG_BIN_DIR")

if PG_BIN_DIR and PG_BIN_DIR not in os.environ["PATH"].split(os.pathsep):
    os.environ["PATH"] = PG_BIN_DIR + os.pathsep + os.environ["PATH"]

os.environ["PSYCOPG_IMPL"] = "python"


# ==========================================
# Database Configuration
# ==========================================

DB_SERVER = os.getenv("DB_SERVER")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

required_settings = {
    "DB_SERVER": DB_SERVER,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "PG_BIN_DIR": PG_BIN_DIR,
}

missing_settings = [
    key for key, value in required_settings.items() if not value
]

if missing_settings:
    raise ValueError(
        f"Missing environment variables: {', '.join(missing_settings)}"
    )


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
        database=database
    )

    return create_engine(url)


# ==========================================
# SQL File Execution
# ==========================================

def run_sql_file(engine):
    sql = BASE_SQL_FILE.read_text(encoding="utf-8")

    with engine.begin() as conn:
        for statement in sql.split(";"):
            if statement.strip():
                conn.execute(text(statement))


# ==========================================
# Database Initialization
# ==========================================

def setup_database():
    engine = get_engine()

    try:
        with engine.begin() as conn:
            conn.execute(
                text("CREATE EXTENSION IF NOT EXISTS vector")
            )

        run_sql_file(engine)

        print("Database:", DB_NAME)
        print("pgvector: Enabled")
        print("Schemas: Bronze, Silver, Gold")
        print("Database setup completed!")

    finally:
        engine.dispose()


if __name__ == "__main__":
    setup_database()
