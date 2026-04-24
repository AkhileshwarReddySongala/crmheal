from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.ghost_service import ghost

router = APIRouter(prefix="/api/export", tags=["export"])
ghost_router = APIRouter(prefix="/api/ghost", tags=["export"])


async def _export_response(batch_id: str):
    csv_text, source = await ghost.export_csv(batch_id)
    if not csv_text:
        raise HTTPException(status_code=404, detail="Batch not found")
    return Response(
        csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=crm-heal-{source}-{batch_id}.csv",
            "X-Export-Source": source,
        },
    )


@router.get("/ghost/{batch_id}")
async def export_ghost(batch_id: str):
    return await _export_response(batch_id)


@router.get("/{batch_id}")
async def export(batch_id: str):
    return await _export_response(batch_id)


@ghost_router.get("/export/{batch_id}")
async def export_ghost_infra(batch_id: str):
    return await _export_response(batch_id)
