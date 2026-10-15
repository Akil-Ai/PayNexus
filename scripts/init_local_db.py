"""Initialize local SQLite database and seed it."""
import os
import sys
import asyncio

# Ensure backend is on sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.db.database import Base, engine, AsyncSessionLocal
from app.models.models import *

async def init_db():
    print("Creating all tables in local database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
