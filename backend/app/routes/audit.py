from fastapi import APIRouter

from app.services.redis_service import state

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/{batch_id}")
async def audit(batch_id: str):
    return {"batch_id": batch_id, "events": await state.get_audit(batch_id)}
