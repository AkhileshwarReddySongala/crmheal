from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.ghost_service import ghost
from app.services.reasoner import reasoner_mode
from app.services.redis_service import state
from app.services.tinyfish_service import tinyfish
from app.services.vapi_service import vapi
import app.main as _main

router = APIRouter(tags=["status"])


@router.get("/health")
async def health():
    ghost_health = await ghost.health()
    return {
        "redis": state.mode,
        "tinyfish": tinyfish.mode(),
        "vapi": vapi.mode(),
        "guild": "linked_via_cli",
        "guild_workspace": settings.guild_workspace_id,
        "guild_workspace_url": settings.guild_workspace_url,
        "guild_agent_name": settings.guild_agent_name,
        "guild_runtime": "local_fastapi",
        "guild_note": "Guild CLI links the agent lifecycle; local Redis audit mirrors session traces.",
        **ghost_health,
        "reasoner": reasoner_mode(),
        "akash_status": "configured" if settings.AKASH_API_KEY else "missing_key",
        "worker": _main.worker_status(),
        "missing_env": {
            "TINYFISH_API_KEY": not bool(settings.tinyfish_api_key),
            "VAPI_API_KEY": not bool(settings.vapi_api_key),
            "VAPI_PHONE_NUMBER_ID": not bool(settings.vapi_phone_number_id),
            "VAPI_WEBHOOK_URL": not bool(settings.vapi_webhook_url),
            "GHOST_DB_URL": not bool(settings.ghost_db_url),
            "AKASH_API_KEY": not bool(settings.AKASH_API_KEY),
        },
    }


@router.get("/api/status/{job_id}")
async def job_status(job_id: str):
    job = await state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/status/batch/{batch_id}")
async def batch_status(batch_id: str):
    batch = await state.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch
