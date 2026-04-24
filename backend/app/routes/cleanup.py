import csv
import io
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.models import CRMLeadRow, JobState
from app.services.discovery import row_issues, summarize
from app.services.guild_service import guild
from app.services.redis_service import state

router = APIRouter(prefix="/api/cleanup", tags=["cleanup"])


@router.post("/start")
async def start_cleanup(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8-sig")
    rows = []
    for raw in csv.DictReader(io.StringIO(content)):
        row = {str(key): (value or "") for key, value in raw.items() if isinstance(key, str)}
        if row.get("id"):
            rows.append(CRMLeadRow(**row))
    batch_id = str(uuid.uuid4())
    jobs = [
        JobState(
            job_id=str(uuid.uuid4()),
            batch_id=batch_id,
            record_id=row.id,
            original=row,
            enriched={"issues": row_issues(row)},
        )
        for row in rows
    ]
    summary = summarize(rows)
    await state.create_batch(batch_id, jobs, summary)
    await guild.log(batch_id, "discovery", "batch_created", {"source": "upload", "after": summary})
    return {"batch_id": batch_id, "summary": summary, "jobs": [job.model_dump(mode="json") for job in jobs]}


@router.post("/launch/{batch_id}")
async def launch_cleanup(batch_id: str):
    batch = await state.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    state.batches[batch_id]["launched"] = True
    await state.publish(batch_id, {"type": "batch_launched", "batch_id": batch_id, "message": "Autonomous cleanup launched."})
    await guild.log(batch_id, "orchestrator", "session_start", {"source": "launch", "after": batch["summary"]})
    for job_id in batch["job_ids"]:
        await state.enqueue_job(job_id)
    return {"batch_id": batch_id, "queued": len(batch["job_ids"])}
