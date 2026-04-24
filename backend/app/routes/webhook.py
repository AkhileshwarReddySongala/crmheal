from fastapi import APIRouter, HTTPException, Request

from app.schemas.models import VapiStructuredData
from app.services.redis_service import state
from app.services.vapi_service import vapi
from app.services.worker import complete_vapi_result, maybe_finalize_batch

router = APIRouter(tags=["webhook"])


@router.post("/api/vapi/webhook")
async def vapi_webhook(request: Request):
    payload = await request.json()
    message = payload.get("message", payload)
    if message.get("type") not in {"end-of-call-report", "call-ended"}:
        return {"ok": True, "ignored": message.get("type")}
    call = message.get("call", {})
    call_id = call.get("id") or message.get("callId") or payload.get("id")
    if not call_id:
        raise HTTPException(status_code=400, detail="Missing call id")
    job_id = await state.job_for_vapi_call(call_id)
    if not job_id:
        raise HTTPException(status_code=404, detail="No job mapped for call")
    job = await state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] == "VERIFIED":
        return {"ok": True, "deduped": True}
    structured = message.get("analysis", {}).get("structuredData") or payload.get("analysis", {}).get("structuredData") or {}
    result = VapiStructuredData(**structured)
    updated = await complete_vapi_result(job, result)
    await maybe_finalize_batch(job["batch_id"])
    return {"ok": True, "job": updated}


@router.post("/api/verify/{job_id}")
async def verify_job(job_id: str):
    job = await state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = await vapi.verify(job)
    if result:
        updated = await complete_vapi_result(job, result)
        await maybe_finalize_batch(job["batch_id"])
        return updated
    return await state.get_job(job_id)
