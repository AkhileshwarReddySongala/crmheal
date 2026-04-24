import time
from typing import Any

from app.schemas.models import AuditEntry
from app.services.redis_service import state


class GuildService:
    def mode(self) -> str:
        return "linked_via_cli"

    async def log(self, batch_id: str, agent: str, action: str, data: dict[str, Any]) -> None:
        entry = AuditEntry(
            batch_id=batch_id,
            job_id=data.get("job_id"),
            record_id=data.get("record_id"),
            agent=agent,
            action=action,
            before=data.get("before"),
            after=data.get("after"),
            confidence=data.get("confidence"),
            source=data.get("source", "guild"),
            mode=self.mode(),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        await state.add_audit(entry)


guild = GuildService()
