from __future__ import annotations

import asyncio
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from os import getenv


ROOT = Path(__file__).resolve().parents[1]


async def run_sql_file(connection: asyncpg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    await connection.execute(sql)


async def main() -> None:
    load_dotenv(ROOT / ".env")
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    connection = await asyncpg.connect(dsn=database_url)
    try:
        await run_sql_file(connection, ROOT / "db" / "init.sql")
        await run_sql_file(connection, ROOT / "db" / "seed.sql")
    finally:
        await connection.close()

    print("Database schema and seed data were loaded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
