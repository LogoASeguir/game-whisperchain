"""
Database connection handler for WhisperChain.
"""

import psycopg2
from psycopg2 import pool
from config import get_config
import sys

config = get_config()

# Connection pool for better performance
connection_pool = None

def init_connection_pool(minconn=1, maxconn=10):
    """Initialize connection pool"""
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn,
            maxconn,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
            connect_timeout=10
        )
        print(f"✓ Connection pool initialized ({minconn}-{maxconn} connections)")
        return True
    except psycopg2.Error as e:
        print(f"✗ Failed to create connection pool: {e}")
        return False

def get_connection():
    """
    Get PostgreSQL connection from pool.
    
    Returns:
        psycopg2.connection or None if connection fails
    """
    global connection_pool
    
    # Initialize pool if not exists
    if connection_pool is None:
        if not init_connection_pool():
            return None
    
    try:
        conn = connection_pool.getconn()
        return conn
    except psycopg2.Error as e:
        print(f"✗ Database connection failed: {e}")
        return None

def return_connection(conn):
    """Return connection to pool"""
    global connection_pool
    if connection_pool and conn:
        connection_pool.putconn(conn)

def close_all_connections():
    """Close all connections in pool"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        print("✓ All database connections closed")

def init_db():
    """Initialize database tables."""
    conn = get_connection()
    if not conn:
        print("✗ Could not connect to database for initialization")
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
                signal_strength INTEGER DEFAULT 70 CHECK (signal_strength >= 0 AND signal_strength <= 100),
                created_at TIMESTAMP DEFAULT NOW(),
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_temporary BOOLEAN DEFAULT TRUE
            )
        ''')
        
        conn.commit()
        print("✓ Database tables initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        conn.rollback()
        return False
        
    finally:
        cur.close()
        return_connection(conn)

def test_connection():
    """Test database connection and return details"""
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    print(f"Host: {config.DB_HOST}")
    print(f"Port: {config.DB_PORT}")
    print(f"Database: {config.DB_NAME}")
    print(f"User: {config.DB_USER}")
    print("-" * 60)
    
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT version();")
            db_version = cur.fetchone()[0]
            print(f"✓ Connection successful!")
            print(f"PostgreSQL version: {db_version[:50]}...")
            
            cur.execute("SELECT current_database(), current_user;")
            db_name, db_user = cur.fetchone()
            print(f"Connected to: {db_name} as {db_user}")
            
            # Test table access
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            print(f"Tables found: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
            
            cur.close()
            return_connection(conn)
            print("=" * 60)
            return True
        except Exception as e:
            print(f"✗ Error during connection test: {e}")
            return_connection(conn)
            print("=" * 60)
            return False
    else:
        print("✗ Connection failed!")
        print("=" * 60)
        return False

if __name__ == "__main__":
    if test_connection():
        print("\nInitializing database...")
        if init_db():
            print("✓ Database is ready!")
            sys.exit(0)
        else:
            print("✗ Database initialization failed")
            sys.exit(1)
    else:
        print("✗ Cannot connect to database")
        sys.exit(1)
