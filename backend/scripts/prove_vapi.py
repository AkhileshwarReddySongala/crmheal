import argparse
import asyncio
import os
import re
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def to_e164(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Prove Vapi outbound calling before full-stack work.")
    parser.add_argument("--phone", default="281-760-6327")
    parser.add_argument("--name", default="Akhileshwar Reddy Songala")
    parser.add_argument("--company", default="Lamar University")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("VAPI_API_KEY", "")
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "")
    if args.mock or not api_key or not phone_number_id:
        print("MOCK VAPI PROOF")
        print({"id": f"mock-{uuid4()}", "customer": to_e164(args.phone), "analysis": {"structuredData": {"phone_verified": True, "title_confirmed": True, "current_company": args.company}}})
        return

    assistant = {
        "firstMessage": f"Hi, this is a quick verification call from CRM Heal. Am I reaching someone at {args.company}?",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": "Keep this verification call under 30 seconds. Ask one question at a time."}],
        },
    }
    webhook_url = os.getenv("VAPI_WEBHOOK_URL", "")
    if webhook_url:
        assistant["server"] = {"url": webhook_url, "timeoutSeconds": 20}
        assistant["serverMessages"] = ["end-of-call-report", "call-ended", "call-failed"]

    payload = {
        "phoneNumberId": phone_number_id,
        "customer": {"number": to_e164(args.phone), "name": args.name},
        "assistant": assistant,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://api.vapi.ai/call/phone", headers={"Authorization": f"Bearer {api_key}"}, json=payload)
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
