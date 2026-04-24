import asyncio
import time
import uuid
from typing import Any

import httpx

from app.config import settings
from app.schemas.models import VapiStructuredData
from app.services.redis_service import state


def to_e164(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"
    return f"+{digits}"


class VapiService:
    def mode(self) -> str:
        if settings.use_mock_vapi or not settings.vapi_api_key or not settings.vapi_phone_number_id:
            return "mock"
        return "configured"

    async def verify(self, job: dict[str, Any]) -> VapiStructuredData | None:
        original = job["original"]
        call_id = f"mock-{uuid.uuid4()}" if self.mode() == "mock" else ""
        if self.mode() == "mock":
            await state.map_vapi_call(call_id, job["job_id"])
            await state.update_job(job["job_id"], status="CALLING_LEAD", progress=70, vapi_call_id=call_id, mode="mock")
            await state.publish(job["batch_id"], {"type": "status_update", "job_id": job["job_id"], "record_id": job["record_id"], "status": "CALLING_LEAD", "progress": 70, "source": "vapi_mock", "message": f"Calling {to_e164(original.get('phone', ''))} via Vapi mock..."})
            await asyncio.sleep(5)
            return VapiStructuredData(phone_verified=True, title_confirmed=True, current_company=original.get("company"), notes="Mock verification succeeded.")

        if not settings.vapi_webhook_url:
            raise RuntimeError("VAPI_WEBHOOK_URL is required for real Vapi verification callbacks")

        assistant = {
            "firstMessage": f"Hi, this is a quick verification call from a database update service. Am I reaching someone at {original.get('company', '')}?",
            "server": {"url": settings.vapi_webhook_url, "timeoutSeconds": 20},
            "serverMessages": ["end-of-call-report", "status-update"],
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": f"You verify whether {original.get('first_name', '')} {original.get('last_name', '')} still works as {original.get('title', '')} at {original.get('company', '')}. Ask one question at a time and keep the call under 30 seconds."}],
            },
            "analysisPlan": {
                "structuredDataPlan": {
                    "enabled": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "phone_verified": {"type": "boolean"},
                            "title_confirmed": {"type": "boolean"},
                            "current_company": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                    },
                }
            },
        }
        payload = {
            "phoneNumberId": settings.vapi_phone_number_id,
            "customer": {"number": to_e164(original.get("phone", "")), "name": f"{original.get('first_name', '')} {original.get('last_name', '')}".strip()},
            "assistant": assistant,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post("https://api.vapi.ai/call/phone", headers={"Authorization": f"Bearer {settings.vapi_api_key}"}, json=payload)
            response.raise_for_status()
            data = response.json()
        call_id = data.get("id") or data.get("call", {}).get("id")
        if call_id:
            await state.map_vapi_call(call_id, job["job_id"])
        await state.update_job(job["job_id"], status="CALL_PENDING", progress=72, vapi_call_id=call_id, mode="configured")
        await state.publish(job["batch_id"], {"type": "status_update", "job_id": job["job_id"], "record_id": job["record_id"], "status": "CALL_PENDING", "progress": 72, "source": "vapi", "message": f"Vapi call started at {time.strftime('%H:%M:%S')}."})
        if call_id:
            asyncio.create_task(self._poll_call_result(call_id, job["job_id"]))
        return None

    async def _poll_call_result(self, call_id: str, job_id: str) -> None:
        from app.schemas.models import JobStatus
        from app.services.worker import complete_vapi_result, maybe_finalize_batch

        deadline = time.monotonic() + max(settings.vapi_timeout_seconds, 30)
        last_status = ""
        while time.monotonic() < deadline:
            await asyncio.sleep(5)
            job = await state.get_job(job_id)
            if not job or job.get("status") == JobStatus.verified.value:
                return
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"https://api.vapi.ai/call/{call_id}", headers={"Authorization": f"Bearer {settings.vapi_api_key}"})
                response.raise_for_status()
                data = response.json()
            last_status = data.get("status") or data.get("endedReason") or last_status
            structured = data.get("analysis", {}).get("structuredData") or data.get("analysis", {}).get("structuredOutputs") or {}
            if structured:
                result = VapiStructuredData(**structured)
                updated = await complete_vapi_result(job, result)
                await maybe_finalize_batch(updated["batch_id"])
                return
            if last_status in {"ended", "completed", "failed", "canceled"}:
                break

        job = await state.get_job(job_id)
        if job and job.get("status") != JobStatus.verified.value:
            await state.update_job(job_id, status=JobStatus.call_timeout.value, progress=100, error=f"Vapi call ended without structured result: {last_status or 'timeout'}", source="vapi")
            await state.publish(job["batch_id"], {"type": "status_update", "job_id": job_id, "record_id": job["record_id"], "status": JobStatus.call_timeout.value, "progress": 100, "source": "vapi", "message": f"Vapi call ended without structured result: {last_status or 'timeout'}."})


vapi = VapiService()
