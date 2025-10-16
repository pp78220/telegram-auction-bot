import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

async def connect_db():
    """Connect to PostgreSQL database"""
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL environment variable not set")
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    """Initialize required tables"""
    conn = await connect_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            username TEXT,
            joined_at TIMESTAMP DEFAULT NOW()
        );
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id SERIAL PRIMARY KEY,
            bid_id TEXT UNIQUE,
            title TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            ended_at TIMESTAMP,
            status TEXT DEFAULT 'active'
        );
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            bid_id TEXT,
            user_id BIGINT,
            username TEXT,
            amount NUMERIC,
            bid_time TIMESTAMP DEFAULT NOW()
        );
    """)
    await conn.close()
