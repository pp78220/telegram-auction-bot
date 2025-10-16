import asyncpg
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")


async def get_connection():
    return await asyncpg.connect(DATABASE_URL)


# 🧩 Initialize DB schema
async def init_db():
    conn = await get_connection()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            joined_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS bids (
            bid_id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            bid_id INT REFERENCES bids(bid_id) ON DELETE CASCADE,
            user_id BIGINT,
            username TEXT,
            amount NUMERIC,
            bid_time TIMESTAMP DEFAULT NOW()
        );
    """)
    await conn.close()


# 🟢 Add new subscriber
async def add_subscriber(user_id, username):
    conn = await get_connection()
    await conn.execute(
        "INSERT INTO subscribers (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user_id, username,
    )
    await conn.close()


# 📢 Get all subscribers
async def get_all_subscribers():
    conn = await get_connection()
    rows = await conn.fetch("SELECT user_id FROM subscribers")
    await conn.close()
    return [r["user_id"] for r in rows]


# 🎯 Create a new auction/bid
async def create_bid(title):
    conn = await get_connection()
    record = await conn.fetchrow(
        "INSERT INTO bids (title) VALUES ($1) RETURNING bid_id, title, created_at",
        title,
    )
    await conn.close()
    return record


# 📜 List all active bids
async def list_active_bids():
    conn = await get_connection()
    rows = await conn.fetch("SELECT * FROM bids ORDER BY bid_id DESC")
    await conn.close()
    return rows


# 💰 Add participant bid
async def add_participant(bid_id, user_id, username, amount):
    conn = await get_connection()
    await conn.execute(
        "INSERT INTO participants (bid_id, user_id, username, amount) VALUES ($1, $2, $3, $4)",
        bid_id, user_id, username, amount,
    )
    await conn.close()


# 🔍 Get bid details
async def get_bid_details(bid_id):
    conn = await get_connection()
    bid = await conn.fetchrow("SELECT * FROM bids WHERE bid_id = $1", bid_id)
    participants = await conn.fetch(
        "SELECT username, amount, bid_time FROM participants WHERE bid_id = $1 ORDER BY amount DESC",
        bid_id,
    )
    await conn.close()
    return bid, participants


# 🛑 End specific auction
async def end_auction(bid_id):
    conn = await get_connection()
    await conn.execute("UPDATE bids SET status = 'ended' WHERE bid_id = $1", bid_id)
    await conn.close()
