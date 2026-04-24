import csv
import io
import json
from typing import Any

from app.config import settings
from app.services.redis_service import state


class GhostService:
    def mode(self) -> str:
        return "connected" if settings.ghost_db_url else "skipped"

    async def health(self) -> dict[str, str]:
        if not settings.ghost_db_url:
            return {"ghost": "skipped", "ghost_reason": "GHOST_DB_URL missing"}
        try:
            import asyncpg

            conn = await asyncpg.connect(settings.ghost_db_url, timeout=3)
            await conn.execute("SELECT 1")
            await conn.close()
            return {"ghost": "connected", "ghost_reason": "connected to GHOST_DB_URL"}
        except Exception as exc:
            return {"ghost": "failed", "ghost_reason": str(exc)}

    async def _log_audit(self, batch_id: str, action: str, payload: dict[str, Any]) -> None:
        from app.services.guild_service import guild

        await guild.log(batch_id, "ghost", action, {"source": "ghost", "after": payload})

    async def persist_batch(self, batch_id: str) -> dict[str, Any]:
        batch = await state.get_batch(batch_id)
        if not batch:
            return {"mode": "failed", "error": "batch not found"}
        jobs = batch["jobs"]
        if not settings.ghost_db_url:
            payload = {
                "type": "ghost_skipped",
                "mode": "skipped",
                "message": "Ghost skipped: GHOST_DB_URL missing",
                "reason": "GHOST_DB_URL missing",
            }
            await state.publish(batch_id, payload)
            await self._log_audit(batch_id, "Ghost skipped: GHOST_DB_URL missing", payload)
            return {"mode": "skipped", "total": len(jobs), "verified": 0, "avg_confidence": 0}
        conn = None
        try:
            import asyncpg

            conn = await asyncpg.connect(settings.ghost_db_url, timeout=5)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clean_leads (
                    id serial primary key,
                    batch_id text not null,
                    record_id text not null,
                    first_name text,
                    last_name text,
                    email text,
                    phone text,
                    company text,
                    title text,
                    status text,
                    confidence numeric,
                    source text,
                    raw_record jsonb,
                    enriched_record jsonb,
                    created_at timestamptz default now()
                )
                """
            )
            await conn.execute("DELETE FROM clean_leads WHERE batch_id = $1", batch_id)
            for job in jobs:
                original = job["original"]
                enriched = job.get("enriched", {})
                await conn.execute(
                    """
                    INSERT INTO clean_leads
                    (batch_id, record_id, first_name, last_name, email, phone, company, title, status, confidence, source, raw_record, enriched_record)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13::jsonb)
                    """,
                    batch_id,
                    str(job["record_id"]),
                    original.get("first_name", ""),
                    original.get("last_name", ""),
                    enriched.get("email") or original.get("email", ""),
                    enriched.get("phone") or original.get("phone", ""),
                    original.get("company", ""),
                    enriched.get("job_title") or original.get("title", ""),
                    job.get("status", ""),
                    int(job.get("confidence", 0)),
                    job.get("source", ""),
                    json.dumps(original),
                    json.dumps(enriched),
                )
            stats = await conn.fetchrow(
                """
                SELECT COUNT(*) AS total,
                       COUNT(CASE WHEN confidence > 85 THEN 1 END) AS verified,
                       COALESCE(AVG(confidence), 0)::float AS avg_confidence
                FROM clean_leads
                WHERE batch_id = $1
                """,
                batch_id,
            )
            payload = {
                "type": "ghost_persisted",
                "mode": "connected",
                "message": "Persisted cleaned CRM to Ghost Postgres",
                "total": stats["total"],
                "verified": stats["verified"],
                "avg_confidence": round(stats["avg_confidence"], 1),
            }
            await state.publish(batch_id, payload)
            await self._log_audit(batch_id, "Persisted cleaned CRM to Ghost Postgres", payload)
            return payload
        except Exception as exc:
            payload = {"type": "ghost_failed", "mode": "failed", "message": str(exc)}
            await state.publish(batch_id, payload)
            await self._log_audit(batch_id, "Ghost persistence failed", payload)
            return payload
        finally:
            if conn:
                await conn.close()

    async def export_csv(self, batch_id: str) -> tuple[str, str]:
        if settings.ghost_db_url:
            try:
                import asyncpg

                conn = await asyncpg.connect(settings.ghost_db_url, timeout=5)
                rows = await conn.fetch(
                    """
                    SELECT record_id, first_name, last_name, email, phone, company, title, status, confidence, source
                    FROM clean_leads
                    WHERE batch_id = $1
                    ORDER BY id
                    """,
                    batch_id,
                )
                await conn.close()
                if rows:
                    output = io.StringIO()
                    fields = ["id", "first_name", "last_name", "email", "phone", "company", "title", "status", "confidence", "source"]
                    writer = csv.DictWriter(output, fieldnames=fields)
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(
                            {
                                "id": row["record_id"],
                                "first_name": row["first_name"] or "",
                                "last_name": row["last_name"] or "",
                                "email": row["email"] or "",
                                "phone": row["phone"] or "",
                                "company": row["company"] or "",
                                "title": row["title"] or "",
                                "status": row["status"] or "",
                                "confidence": row["confidence"] or 0,
                                "source": row["source"] or "",
                            }
                        )
                    return output.getvalue(), "ghost"
            except Exception:
                pass

        batch = await state.get_batch(batch_id)
        if not batch:
            return "", "fallback"
        output = io.StringIO()
        fields = ["id", "first_name", "last_name", "email", "phone", "company", "title", "status", "confidence", "source"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for job in batch["jobs"]:
            original = job["original"]
            enriched = job.get("enriched", {})
            writer.writerow(
                {
                    "id": job["record_id"],
                    "first_name": original.get("first_name", ""),
                    "last_name": original.get("last_name", ""),
                    "email": enriched.get("email") or original.get("email", ""),
                    "phone": enriched.get("phone") or original.get("phone", ""),
                    "company": original.get("company", ""),
                    "title": enriched.get("job_title") or original.get("title", ""),
                    "status": job.get("status", ""),
                    "confidence": job.get("confidence", 0),
                    "source": job.get("source", ""),
                }
            )
        return output.getvalue(), "fallback"


ghost = GhostService()
