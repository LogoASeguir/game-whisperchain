# database.py
"""
Database connection handler for WhisperChain.
Simplified single-user connection.
"""

import psycopg2
from config import get_config

config = get_config()


def get_connection():
    """
    Get PostgreSQL connection.

    Returns:
        psycopg2.connection or None if connection fails
    """
    try:
        conn = psycopg2.connect(
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        return conn
    except psycopg2.Error as e:
        print(f"Database connection failed: {e}")
        return None


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    if not conn:
        print("Could not connect to database for initialization")
        return False

    cur = conn.cursor()

    try:
        # Games history table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS games_history (
                id SERIAL PRIMARY KEY,
                room_code TEXT NOT NULL,
                num_players INTEGER NOT NULL,
                rounds JSONB NOT NULL,
                player_results JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                closed_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        # Users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                signal_strength INTEGER DEFAULT 50 CHECK (signal_strength >= 10 AND signal_strength <= 100),
                created_at TIMESTAMP DEFAULT NOW(),
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_temporary BOOLEAN DEFAULT TRUE
            )
        ''')

        conn.commit()
        print("Database tables initialized")
        return True

    except Exception as e:
        print(f"Database initialization failed: {e}")
        conn.rollback()
        return False

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)

    conn = get_connection()
    if conn:
        print("Connection successful")
        cur = conn.cursor()
        cur.execute("SELECT current_database(), current_user;")
        db_name, db_user = cur.fetchone()
        print(f"Database: {db_name}")
        print(f"User: {db_user}")
        cur.close()
        conn.close()

    if init_db():
        print("Database ready")

    print("=" * 60)
