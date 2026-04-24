import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.redis_service import state

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/{batch_id}")
async def events(batch_id: str, request: Request):
    async def stream():
        queue = await state.subscribe(batch_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            state.unsubscribe(batch_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")
