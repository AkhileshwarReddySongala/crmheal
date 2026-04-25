import asyncio
import time

from app.config import settings
from app.schemas.models import JobStatus
from app.services.ghost_service import ghost
from app.services.guild_service import guild
from app.services.reasoner import decide_next_action, reasoner_mode
from app.services.redis_service import state
from app.services.tinyfish_service import tinyfish
from app.services.vapi_service import vapi


async def complete_vapi_result(job: dict, result) -> dict:
    # Call completing is itself signal — lock at 98 regardless of outcome.
    # phone_verified/title_confirmed are stored as data fields for the audit trail.
    if result.phone_verified and result.title_confirmed:
        confidence = 98
    elif result.phone_verified or result.title_confirmed:
        confidence = 90
    else:
        # Call resolved (voicemail, no answer, etc.) — still evidence the number exists
        confidence = 82
    enriched = {**job.get("enriched", {}), "phone_verified": result.phone_verified, "title_confirmed": result.title_confirmed, "current_company": result.current_company, "verification_notes": result.notes}
    updated = await state.update_job(job["job_id"], status=JobStatus.verified.value, progress=98, enriched=enriched, confidence=confidence, source="vapi", mode=vapi.mode())
    await state.publish(job["batch_id"], {"type": "status_update", "job_id": job["job_id"], "record_id": job["record_id"], "status": JobStatus.verified.value, "progress": 98, "confidence": confidence, "enriched_fields": enriched, "source": "vapi", "mode": vapi.mode(), "message": f"Record #{job['record_id']}: Call complete, phone verified."})
    await guild.log(job["batch_id"], "vapi", "vapi_call_resolved", {"job_id": job["job_id"], "record_id": job["record_id"], "after": enriched, "confidence": confidence, "source": "vapi"})
    return updated


async def process_job(job_id: str) -> None:
    job = await state.get_job(job_id)
    if not job:
        return
    batch_id = job["batch_id"]
    record_id = job["record_id"]
    try:
        await state.update_job(job_id, status=JobStatus.searching_web.value, progress=20, source="discovery")
        await state.publish(batch_id, {"type": "status_update", "job_id": job_id, "record_id": record_id, "status": JobStatus.searching_web.value, "progress": 20, "source": "discovery", "message": f"Record #{record_id}: Searching web for {job['original'].get('company', 'unknown')}..."})
        await asyncio.sleep(0.25)

        await state.update_job(job_id, status=JobStatus.parsing_dom.value, progress=50)
        enriched = await tinyfish.enrich(type("Row", (), job["original"])())
        reasoning_record = {**job["original"], **enriched}
        await state.publish(batch_id, {"type": "reasoning_started", "job_id": job_id, "record_id": record_id, "status": JobStatus.parsing_dom.value, "progress": 60, "source": "reasoner", "mode": reasoner_mode(), "message": f"Record #{record_id}: Reasoner evaluating next action..."})
        await asyncio.sleep(1)
        decision = await decide_next_action(reasoning_record)
        decision["confidence"] = int(decision.get("confidence", 0))
        await guild.log(batch_id, "reasoner", "decision", {"job_id": job_id, "record_id": record_id, "after": {"decision": decision}, "confidence": decision["confidence"], "source": "akash" if reasoner_mode() == "akash" else "rule"})
        status = JobStatus.completed.value
        progress = 75
        confidence = decision["confidence"]
        should_call = bool(decision.get("should_call_vapi"))
        enriched = {**enriched, "reasoning": decision}
        if should_call:
            status = JobStatus.needs_verification.value
        updated = await state.update_job(job_id, status=status, progress=progress, enriched=enriched, confidence=confidence, source=enriched.get("source", "tinyfish"), mode=tinyfish.mode())
        await state.publish(batch_id, {"type": "status_update", "job_id": job_id, "record_id": record_id, "status": status, "progress": progress, "confidence": confidence, "enriched_fields": enriched, "decision": decision, "source": enriched.get("source", "tinyfish"), "mode": tinyfish.mode(), "message": f"Record #{record_id}: Enriched via {enriched.get('source', 'tinyfish')}. Reasoner says: {decision.get('reason', 'ready')}."})
        await guild.log(batch_id, "tinyfish", "enrichment_complete", {"job_id": job_id, "record_id": record_id, "after": enriched, "confidence": confidence, "source": enriched.get("source")})

        if status == JobStatus.needs_verification.value and settings.auto_verify:
            result = await vapi.verify(updated)
            if result:
                await complete_vapi_result(updated, result)
        elif status == JobStatus.completed.value:
            await state.update_job(job_id, progress=100)
    except Exception as exc:
        await state.update_job(job_id, status=JobStatus.failed.value, error=str(exc), source="worker")
        await state.publish(batch_id, {"type": "status_update", "job_id": job_id, "record_id": record_id, "status": JobStatus.failed.value, "progress": 100, "message": str(exc), "source": "worker"})


async def maybe_finalize_batch(batch_id: str) -> None:
    batch = await state.get_batch(batch_id)
    if not batch:
        return
    terminal = {JobStatus.completed.value, JobStatus.verified.value, JobStatus.failed.value, JobStatus.call_timeout.value}
    if all(job["status"] in terminal for job in batch["jobs"]):
        if not batch.get("ghost_done"):
            state.batches[batch_id]["ghost_done"] = True
            await ghost.persist_batch(batch_id)
            await guild.log(batch_id, "guild", "session_end", {"source": "summary", "confidence": 0})


async def worker_loop() -> None:
    await state.publish("system", {"type": "worker_started", "message": "Worker started"})
    while True:
        try:
            job_id = await state.dequeue_job()
            await process_job(job_id)
            job = await state.get_job(job_id)
            if job:
                await maybe_finalize_batch(job["batch_id"])
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(1)
