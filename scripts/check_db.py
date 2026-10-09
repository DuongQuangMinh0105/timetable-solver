import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load database configuration from the .env file
load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from .env")

# Create a database engine
engine = create_engine(database_url)

# Connect to PostgreSQL and execute a test query
try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Database connection successful!")
        print("Test query result:", result.scalar())
finally:
    engine.dispose()
