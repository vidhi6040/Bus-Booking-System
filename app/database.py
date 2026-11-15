import os
import mysql.connector
from dotenv import load_dotenv
load_dotenv()

def get_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "bus_booking_db"),
            autocommit=False
        )
    except mysql.connector.Error as exc:
        print("MySQL connection failed:", exc)
        return None
