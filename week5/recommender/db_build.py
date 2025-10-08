import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

CONNECTION = os.getenv("TIMESCALE_CONNECTION_STRING")

# need to run this to enable vector data type
CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector"

CREATE_PODCAST_TABLE = """
CREATE TABLE IF NOT EXISTS podcast (
  id TEXT PRIMARY KEY,
  title TEXT
)
"""

CREATE_SEGMENT_TABLE = """
CREATE TABLE IF NOT EXISTS podcast_segment (
  id TEXT PRIMARY KEY,
  start_time FLOAT,
  end_time FLOAT,
  content TEXT,
  embedding VECTOR(128),
  podcast_id TEXT,
  FOREIGN KEY (podcast_id) REFERENCES podcast (id)
)
"""

conn = psycopg2.connect(CONNECTION)
conn.cursor().execute(CREATE_EXTENSION)
conn.cursor().execute(CREATE_PODCAST_TABLE)
conn.cursor().execute(CREATE_SEGMENT_TABLE)
conn.commit()
conn.close()
