# db.py
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime

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

    # Bids table (bid_id is SERIAL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            bid_id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            ended_at TIMESTAMP
        )
    """)

    # Participants table (store telegram_id instead of username)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            bid_id INTEGER REFERENCES bids(bid_id) ON DELETE CASCADE,
            telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
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
async def create_bid(title: str):
    """Create a new bid and return its ID."""
    conn = await get_db_connection()
    bid_id = await conn.fetchval("""
        INSERT INTO bids (title, created_at)
        VALUES ($1, NOW())
        RETURNING bid_id
    """, title)
    await conn.close()
    return bid_id


async def list_active_bids():
    conn = await get_db_connection()
    rows = await conn.fetch("""
        SELECT bid_id, title, created_at, status
        FROM bids
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)
    await conn.close()
    return rows


async def add_participant(bid_id: int, telegram_id: int, amount: float):
    """Add a participant to a bid."""
    conn = await get_db_connection()
    await conn.execute("""
        INSERT INTO participants (bid_id, telegram_id, amount, bid_time)
        VALUES ($1, $2, $3, NOW())
    """, bid_id, telegram_id, amount)
    await conn.close()


async def get_bid_details(bid_id: int):
    conn = await get_db_connection()
    bid = await conn.fetchrow("SELECT * FROM bids WHERE bid_id=$1", bid_id)
    participants = await conn.fetch("""
        SELECT u.username, u.telegram_id, p.amount, p.bid_time
        FROM participants p
        JOIN users u ON p.telegram_id = u.telegram_id
        WHERE p.bid_id=$1
        ORDER BY p.bid_time DESC
    """, bid_id)
    await conn.close()
    return bid, participants


async def end_auction(bid_id: int):
    conn = await get_db_connection()
    await conn.execute("""
        UPDATE bids
        SET status='ended', ended_at=NOW()
        WHERE bid_id=$1
    """, bid_id)
    await conn.close()


async def get_monthly_report_data(months: int):
    conn = await get_db_connection()
    rows = await conn.fetch("""
        SELECT b.bid_id, b.title, p.telegram_id, u.username, p.amount, p.bid_time
        FROM participants p
        JOIN bids b ON p.bid_id = b.bid_id
        JOIN users u ON u.telegram_id = p.telegram_id
        WHERE b.created_at >= NOW() - ($1 || ' months')::INTERVAL
        ORDER BY b.bid_id, p.bid_time
    """, months)
    await conn.close()
    return rows
