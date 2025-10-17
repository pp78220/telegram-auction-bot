# db.py
import asyncpg
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# ------------------ DB Connection ------------------
async def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not set")
    return await asyncpg.connect(DATABASE_URL)


# ------------------ Init Tables ------------------
async def init_db():
    
    """Initialize database and create tables if they don't exist."""
    conn = await get_db_connection()

    # Users table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id BIGINT PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Bids table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            bid_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """)

    # Participants table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            bid_id TEXT REFERENCES bids(bid_id) ON DELETE CASCADE,
            telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
            username TEXT,
            amount NUMERIC NOT NULL,
            bid_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await conn.close()


# ------------------ Subscribers ------------------
async def add_subscriber(telegram_id: int, username: str):
    conn = await get_db_connection()
    await conn.execute("""
        INSERT INTO users (telegram_id, username)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO NOTHING
    """, telegram_id, username)
    await conn.close()


async def get_all_subscribers():
    conn = await get_db_connection()
    rows = await conn.fetch("SELECT telegram_id, username FROM users")
    await conn.close()
    return rows


# ------------------ Bids ------------------
async def create_bid(bid_id: str, title: str):
    conn = await get_db_connection()
    await conn.execute("""
        INSERT INTO bids (bid_id, title, created_at)
        VALUES ($1, $2, NOW())
    """, bid_id, title)
    await conn.close()


async def list_active_bids():
    conn = await get_db_connection()
    rows = await conn.fetch("SELECT bid_id, title, created_at, status FROM bids WHERE status='active'")
    await conn.close()
    return rows


async def add_participant(bid_id: str, user_id: int, username: str, amount: float):
    conn = await get_db_connection()
    await conn.execute("""
        INSERT INTO participants (bid_id, user_id, username, amount, bid_time)
        VALUES ($1, $2, $3, $4, NOW())
    """, bid_id, user_id, username, amount)
    await conn.close()


async def get_bid_details(bid_id: str):
    conn = await get_db_connection()
    bid = await conn.fetchrow("SELECT * FROM bids WHERE bid_id=$1", bid_id)
    participants = await conn.fetch("SELECT username, amount, bid_time FROM participants WHERE bid_id=$1", bid_id)
    await conn.close()
    return bid, participants


async def end_auction(bid_id: str):
    conn = await get_db_connection()
    await conn.execute("UPDATE bids SET status='ended', ended_at=NOW() WHERE bid_id=$1", bid_id)
    await conn.close()