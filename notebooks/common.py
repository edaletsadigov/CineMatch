# Standard libraries
import os
import sys
import json
import re
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import text, create_engine, URL
from dotenv import load_dotenv
import requests
import gzip
from datetime import datetime, timezone

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
TMDB_API_TOKEN = os.getenv("TMDB_API_TOKEN")
DB_SERVER = os.getenv("DB_SERVER")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

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