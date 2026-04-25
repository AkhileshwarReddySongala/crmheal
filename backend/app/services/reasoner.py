import json
import re
from typing import Any

import httpx

from app.config import settings


def _existing_confidence(record: dict[str, Any], calculated: int) -> int:
    value = record.get("confidence")
    if isinstance(value, (int, float)):
        return max(0, min(calculated, int(value)))
    return calculated


async def rule_based_reasoning(record: dict[str, Any]):
    issues = []

    if not record.get("email") or "@" not in record.get("email", ""):
        issues.append("missing_or_invalid_email")

    if not record.get("title") and not record.get("job_title"):
        issues.append("missing_title")

    if record.get("status") == "stale":
        issues.append("stale_record")

    confidence = _existing_confidence(record, max(0, 100 - (len(issues) * 20)))

    return {
        "issues": issues,
        "confidence": confidence,
        "should_enrich": len(issues) > 0,
        "should_call_vapi": bool(record.get("phone") and confidence < 80),
        "reason": "rule-based evaluation",
    }


async def akash_reasoning(record: dict[str, Any]):
    if not settings.AKASH_API_KEY:
        raise RuntimeError("AKASH_API_KEY is required when REASONER_PROVIDER=akash")

    prompt = f"""
You are an autonomous CRM cleanup agent.

Analyze this record and return STRICT JSON:

{{
  "issues": [],
  "confidence": number (0-100),
  "should_enrich": boolean,
  "should_call_vapi": boolean,
  "reason": string
}}

Record:
{record}

Rules:
- Missing email -> issue
- Missing title -> issue
- Invalid email -> issue
- Stale status -> issue
- Confidence decreases per issue
- If confidence < 80 AND phone exists -> should_call_vapi = true
- Output ONLY JSON, no explanation
"""

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.AKASH_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AKASH_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.AKASH_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.S)
            if not match:
                raise
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("Akash response was not a JSON object")
        parsed.setdefault("issues", [])
        parsed.setdefault("confidence", 0)
        parsed.setdefault("should_enrich", bool(parsed["issues"]))
        parsed.setdefault("should_call_vapi", bool(record.get("phone") and int(parsed["confidence"]) < 80))
        parsed.setdefault("reason", "akash evaluation")
        return parsed

    except Exception as exc:
        raise RuntimeError(f"Akash reasoning failed: {type(exc).__name__}: {exc or 'no message'}") from exc


async def decide_next_action(record: dict[str, Any]):
    if settings.USE_LLM_REASONING and settings.REASONER_PROVIDER == "akash":
        return await akash_reasoning(record)
    return await rule_based_reasoning(record)


def reasoner_mode() -> str:
    if settings.USE_LLM_REASONING and settings.REASONER_PROVIDER == "akash" and settings.AKASH_API_KEY:
        return "akash"
    return "rule"
