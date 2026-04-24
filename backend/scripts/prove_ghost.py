import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


async def main() -> None:
    url = os.getenv("GHOST_DB_URL", "")
    if not url:
        print("GHOST_DB_URL missing. Skipping Ghost proof.")
        return
    import asyncpg

    conn = await asyncpg.connect(url)
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS clean_leads (
            batch_id text,
            record_id int,
            first_name text,
            last_name text,
            email text,
            phone text,
            company text,
            title text,
            confidence int,
            source text,
            updated_at timestamptz default now()
        )
        """
    )
    await conn.execute("DELETE FROM clean_leads WHERE batch_id = 'ghost-proof'")
    await conn.execute(
        """
        INSERT INTO clean_leads
        (batch_id, record_id, first_name, last_name, email, phone, company, title, confidence, source)
        VALUES ('ghost-proof', 17, 'Akhileshwar Reddy', 'Songala', 'akhil@example.com', '281-760-6327', 'Lamar University', 'Student Technology Associate', 98, 'proof')
        """
    )
    row = await conn.fetchrow(
        """
        SELECT COUNT(*) AS total,
               COUNT(CASE WHEN confidence > 85 THEN 1 END) AS verified,
               AVG(confidence)::float AS avg_confidence
        FROM clean_leads
        WHERE batch_id = 'ghost-proof'
        """
    )
    await conn.close()
    print(dict(row))


if __name__ == "__main__":
    asyncio.run(main())
