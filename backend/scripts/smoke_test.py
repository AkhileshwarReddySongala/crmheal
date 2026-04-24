import asyncio
from pathlib import Path

import httpx


async def main() -> None:
    base = "http://localhost:8000"
    async with httpx.AsyncClient(timeout=30) as client:
        health = (await client.get(f"{base}/health")).json()
        print("health", health)
        csv_path = Path(__file__).resolve().parents[2] / "data" / "dirty_crm.csv"
        with csv_path.open("rb") as handle:
            start = await client.post(f"{base}/api/cleanup/start", files={"file": ("dirty_crm.csv", handle, "text/csv")})
        start.raise_for_status()
        batch = start.json()
        print("batch", batch["batch_id"], batch["summary"])
        launch = await client.post(f"{base}/api/cleanup/launch/{batch['batch_id']}")
        launch.raise_for_status()
        await asyncio.sleep(8)
        status = (await client.get(f"{base}/api/status/batch/{batch['batch_id']}")).json()
        print("jobs", len(status["jobs"]))
        export = await client.get(f"{base}/api/export/{batch['batch_id']}")
        export.raise_for_status()
        print("export_bytes", len(export.text))


if __name__ == "__main__":
    asyncio.run(main())
