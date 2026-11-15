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