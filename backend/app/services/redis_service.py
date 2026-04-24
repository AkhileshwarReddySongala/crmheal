import asyncio
import json
import time
from collections import defaultdict, deque
from typing import Any

from app.config import settings
from app.schemas.models import AuditEntry, JobState


class StateService:
    def __init__(self) -> None:
        self.redis = None
        self.mode = "memory"
        self.jobs: dict[str, dict[str, Any]] = {}
        self.batches: dict[str, dict[str, Any]] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.audit: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.events: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        self.subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self.vapi_calls: dict[str, str] = {}

    async def connect(self) -> None:
        try:
            import redis.asyncio as redis

            client = redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self.redis = client
            self.mode = "redis"
        except Exception:
            self.redis = None
            self.mode = "memory"

    async def close(self) -> None:
        if self.redis:
            await self.redis.aclose()

    async def create_batch(self, batch_id: str, rows: list[JobState], summary: dict[str, Any]) -> None:
        self.batches[batch_id] = {
            "batch_id": batch_id,
            "summary": summary,
            "job_ids": [row.job_id for row in rows],
            "launched": False,
            "created_at": time.time(),
        }
        for row in rows:
            await self.set_job(row)

    async def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        batch = self.batches.get(batch_id)
        if not batch:
            return None
        jobs = [await self.get_job(job_id) for job_id in batch["job_ids"]]
        return {**batch, "jobs": [job for job in jobs if job]}

    async def set_job(self, job: JobState) -> None:
        payload = job.model_dump(mode="json")
        self.jobs[job.job_id] = payload
        if self.redis:
            await self.redis.hset(f"job:{job.job_id}", mapping={"payload": json.dumps(payload)})

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        if self.redis:
            raw = await self.redis.hget(f"job:{job_id}", "payload")
            if raw:
                return json.loads(raw)
        return self.jobs.get(job_id)

    async def update_job(self, job_id: str, **updates: Any) -> dict[str, Any]:
        current = await self.get_job(job_id)
        if not current:
            raise KeyError(job_id)
        current.update({k: v for k, v in updates.items() if v is not None})
        self.jobs[job_id] = current
        if self.redis:
            await self.redis.hset(f"job:{job_id}", mapping={"payload": json.dumps(current)})
        return current

    async def enqueue_job(self, job_id: str) -> None:
        await self.queue.put(job_id)
        if self.redis:
            await self.redis.rpush("queue:enrichment", job_id)

    async def dequeue_job(self) -> str:
        if self.redis:
            item = await self.redis.blpop("queue:enrichment", timeout=1)
            if item:
                return item[1]
        return await self.queue.get()

    async def publish(self, batch_id: str, event: dict[str, Any]) -> None:
        event = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
        self.events[batch_id].append(event)
        while len(self.events[batch_id]) > 500:
            self.events[batch_id].popleft()
        if self.redis:
            await self.redis.xadd(f"events:{batch_id}", {"payload": json.dumps(event)}, maxlen=500)
        for subscriber in list(self.subscribers[batch_id]):
            await subscriber.put(event)

    async def subscribe(self, batch_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.subscribers[batch_id].add(queue)
        for event in self.events[batch_id]:
            await queue.put(event)
        return queue

    def unsubscribe(self, batch_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.subscribers[batch_id].discard(queue)

    async def add_audit(self, entry: AuditEntry) -> None:
        payload = entry.model_dump(mode="json")
        self.audit[entry.batch_id].append(payload)
        if self.redis:
            await self.redis.rpush(f"audit:{entry.batch_id}", json.dumps(payload))
        await self.publish(entry.batch_id, {"type": "audit_event", **payload})

    async def get_audit(self, batch_id: str) -> list[dict[str, Any]]:
        if self.redis:
            rows = await self.redis.lrange(f"audit:{batch_id}", 0, -1)
            if rows:
                return [json.loads(row) for row in rows]
        return self.audit.get(batch_id, [])

    async def map_vapi_call(self, call_id: str, job_id: str) -> None:
        self.vapi_calls[call_id] = job_id
        if self.redis:
            await self.redis.set(f"vapi_call:{call_id}", job_id, ex=3600)

    async def job_for_vapi_call(self, call_id: str) -> str | None:
        if self.redis:
            value = await self.redis.get(f"vapi_call:{call_id}")
            if value:
                return value
        return self.vapi_calls.get(call_id)


state = StateService()
