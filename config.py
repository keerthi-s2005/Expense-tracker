import os

# Configure these environment variables on your computer before running the app.
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "expenses_tracker")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-development-secret")
