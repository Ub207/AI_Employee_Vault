import asyncio
import os
import sys

# Add the project root to sys.path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import engine, init_db, Base
from backend.models.task import Task
from backend.models.approval import Approval
from backend.models.log import Log
from backend.models.sla import SLARecord
from sqlalchemy import text

async def test_connection():
    print("⏳ Testing Database Connection...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Connected! PostgreSQL Version: {version}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("\nFix: Ensure PostgreSQL is running and database 'digital_fte' exists.")
        print("Command: CREATE DATABASE digital_fte;")
        return

    print("\n⏳ Creating Tables...")
    try:
        await init_db()
        print("✅ Tables Created Successfully!")
    except Exception as e:
        print(f"❌ Table Creation Failed: {e}")
        return

    print("\n⏳ Verifying Tables in Database...")
    try:
        async with engine.connect() as conn:
            # Query to list tables in public schema
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
            ))
            tables = [row[0] for row in result.fetchall()]
            print(f"✅ Found Tables: {tables}")
            
            if "tasks" in tables:
                print("🎉 SUCCESS: 'tasks' table exists.")
            else:
                print("⚠️ WARNING: 'tasks' table missing despite init_db() success.")

    except Exception as e:
        print(f"❌ Verification Failed: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_connection())
