# CRM Heal

Autonomous AI agent that cleans, enriches, and verifies CRM data end-to-end — no human in the loop.

Upload a dirty CSV. One click. The agent detects duplicates, fills gaps via TinyFish web scraping, makes real Vapi outbound calls to verify low-confidence phone records, logs every decision to Guild.ai, and exports a clean CSV.

**Built at the Ship to Prod Agentic Engineering Hackathon — April 24, 2026.**

---

## Architecture

```
CSV Upload
    |
    v
FastAPI  POST /api/cleanup/start   ─── parse rows, detect issues, create jobs
FastAPI  POST /api/cleanup/launch  ─── enqueue all jobs to worker
    |
    v
Redis / In-Memory Queue (asyncio.Queue fallback)
    |
    v
Worker Loop (BRPOP / asyncio)
    |
    +── TinyFish Stage 1: Search API  ─── find company URL
    +── TinyFish Stage 2: Fetch API   ─── extract contact fields from page
    +── Akash / Rule Reasoner         ─── decide: enrich_only or call_vapi
    |
    +── [if confidence < 80% and phone exists]
    |       Vapi Outbound Call  ─── real phone call to verify contact
    |       Vapi Webhook        ─── POST /api/vapi/webhook ← structured result
    |
    +── Guild.ai HTTP log       ─── session_start, enrichment_complete, vapi_*, session_end
    +── Ghost Postgres          ─── persist clean_leads (optional)
    |
    v
SSE Stream  GET /api/events/{batch_id}  ─── Redis Streams or in-memory pub/sub
    |
    v
React Dashboard
    +── Confidence meter 0 → 25 → 50 → 75 → 98%
    +── Guild.ai audit trail panel (live scroll)
    +── Activity feed
    +── "Verify" button  POST /api/verify/{job_id}
```

---

## Quick Start

```powershell
cd crm-heal
Copy-Item .env.example .env
# Edit .env — fill in your API keys
.\scripts\dev.ps1 -Install
```

Open:
- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`

Upload `data/dirty_crm.csv`, review the issues summary, click **Launch Cleanup**, then click **Verify** on Record 17 when it reaches `Needs Call`.

---

## Sponsor Integrations

| Tool | Role | Visible in demo |
|------|------|-----------------|
| **Redis** | Job queue (BRPOP), job state (hashes), SSE (Streams), enrichment cache | `redis: memory/connected` on `/health` |
| **TinyFish** | 2-stage web scraping: Search → Fetch | Live enrichment of all 30 records |
| **Vapi** | Outbound call + structured output via webhook | Record 17 phone rings on stage |
| **Guild.ai** | Agent control plane: register, log sessions, audit trail | Live audit panel + workspace dashboard |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_URL` | `redis://localhost:6379` | Redis Cloud or local. Falls back to in-memory automatically. |
| `TINYFISH_API_KEY` | — | Real TinyFish enrichment. Empty = mock mode. |
| `USE_MOCK_TINYFISH` | `false` | Force mock TinyFish regardless of key. |
| `VAPI_API_KEY` | — | Real Vapi outbound calls. Empty = mock mode. |
| `VAPI_PHONE_NUMBER_ID` | — | Vapi phone number to call from. |
| `VAPI_WEBHOOK_URL` | — | Public HTTPS URL for Vapi call-ended webhook (ngrok / Cloudflare tunnel). |
| `VAPI_TIMEOUT_SECONDS` | `45` | Max wait for call structured result before timeout. |
| `USE_MOCK_VAPI` | `false` | Force mock Vapi (5s delay, returns success). |
| `AUTO_VERIFY` | `false` | Worker auto-calls Vapi for low-confidence records. Set `true` for fully autonomous mode. |
| `DEMO_VERIFY_BUTTON` | `true` | Show manual Verify button in UI for stage-controlled demo. |
| `GUILD_WORKSPACE_ID` | `zxc` | Guild.ai workspace slug. |
| `GUILD_WORKSPACE_URL` | — | Full workspace URL shown in health endpoint. |
| `GUILD_AGENT_NAME` | `crm-heal` | Agent name in Guild.ai hub. |
| `GHOST_DB_URL` | — | TimescaleDB/Postgres connection string. Enables Ghost persistence. |
| `REASONER_PROVIDER` | `akash` | `rule` or `akash`. |
| `USE_LLM_REASONING` | `true` | Enable Akash LLM reasoning when key present. Falls back to rule mode. |
| `AKASH_API_KEY` | — | Akash ML API key (OpenAI-compatible). |
| `AKASH_BASE_URL` | `https://api.akashml.com/v1` | Akash base URL. |
| `AKASH_MODEL` | `meta-llama/Llama-3.3-70B-Instruct` | Reasoning model. |

---

## API Routes

```
POST /api/cleanup/start          Upload CSV → parse, detect issues → returns batch + jobs
POST /api/cleanup/launch/{id}    Enqueue all jobs to worker → starts autonomous pipeline
GET  /api/status/{job_id}        Single job state (polling fallback)
GET  /api/status/batch/{id}      All jobs in batch
GET  /api/events/{batch_id}      SSE stream — progress 0/25/50/75/98, audit events
POST /api/verify/{job_id}        Manual Vapi trigger for a specific job
POST /api/vapi/webhook           Vapi call-ended receiver → parse structuredData
GET  /api/audit/{batch_id}       Full audit trail (all Guild.ai logged events)
GET  /api/export/{batch_id}      Clean CSV download (Ghost-first, Redis fallback)
GET  /api/ghost/export/{id}      Ghost Postgres export (X-Export-Source header)
GET  /health                     Service status + integration health
```

---

## Confidence Score

The frontend confidence meter advances through 4 fixed checkpoints:

| Stage | Progress | Trigger |
|-------|----------|---------|
| Job created | 0% | Upload |
| TinyFish Stage 1 complete | 25% | URL found via search |
| TinyFish Stage 2 complete | 50% | Markdown fetched, fields extracted |
| Reasoner decision | 75% | Enrichment complete (hard cap until Vapi) |
| Vapi verified | 98% | Call resolved with structured confirmation |

98%, not 100% — AI systems shouldn't claim certainty.

---

## Demo Flow (3-minute script)

1. Upload `data/dirty_crm.csv` → issues summary shows 4 duplicate pairs, 6 missing fields
2. Click **Launch Cleanup** → watch the activity feed and confidence meters animate
3. Navigate to Record 17 (Akhileshwar Reddy Songala, Lamar University)
4. When status shows **Needs Call**, click **Verify**
5. Phone rings at 281-760-6327 → answer and confirm → confidence locks at 98% + ding
6. Open Guild.ai workspace to show audit trail
7. Click Export to download clean CSV

**Demo mode settings:** `AUTO_VERIFY=false`, `DEMO_VERIFY_BUTTON=true`

---

## Proof Scripts

```powershell
cd crm-heal\backend

# Test Vapi in isolation (run before full stack)
python scripts\prove_vapi.py --mock   # mock mode, no real call
python scripts\prove_vapi.py          # real call to configured phone number

# Test Ghost persistence
python scripts\prove_ghost.py

# Full smoke test (backend must be running)
python scripts\smoke_test.py
```

---

## Webhook Setup (Vapi)

Vapi needs a public HTTPS URL to deliver call results. Use ngrok or a Cloudflare tunnel:

```bash
# Option A: ngrok
ngrok http 8000
# Copy the HTTPS URL → set VAPI_WEBHOOK_URL=https://xxxx.ngrok.io/api/vapi/webhook

# Option B: Cloudflare
cloudflared tunnel --url http://localhost:8000
# Copy the URL → set VAPI_WEBHOOK_URL=https://xxxx.trycloudflare.com/api/vapi/webhook
```

Update `VAPI_WEBHOOK_URL` in `.env` and restart the backend. Test the tunnel is alive:
```bash
curl -X POST $VAPI_WEBHOOK_URL -H "Content-Type: application/json" -d '{"test":true}'
```

---

## Reasoning Modes

**Rule mode** (no API key required): evaluates missing/invalid email, missing title, stale status, and low confidence. Scales to Vapi if phone exists and confidence < 80%.

**Akash mode** (`REASONER_PROVIDER=akash`): sends a structured JSON prompt to Llama-3.3-70B-Instruct via Akash's OpenAI-compatible API. Returns `should_call_vapi`, `confidence`, and `reason`. Falls back to rule mode on timeout, API error, or JSON parse failure.

---

## Guild.ai Setup

```bash
npm i @guildai/cli -g
guild auth login
guild workspace select   # select workspace "zxc"
guild agent init --name crm-heal --template BLANK
guild agent save --message "CRM Heal agent init"
guild agent publish
```

FastAPI does not call Guild APIs directly. The Guild CLI links the agent lifecycle. All audit events are logged via HTTP POST and mirrored locally in Redis / in-memory audit lists.

---

## Ghost Setup

```bash
curl -fsSL https://install.ghost.build | sh
ghost login
ghost create
ghost connect <db-name>
```

Set `GHOST_DB_URL` to a TimescaleDB/Postgres connection string. After each batch completes, CRM Heal writes cleaned rows to `clean_leads`. If Ghost is unavailable, export falls back to in-memory state with `X-Export-Source: fallback` header.

---

## Judging Criteria

| Criterion | How CRM Heal delivers |
|-----------|-----------------------|
| **Autonomy** | Upload → launch → zero clicks until Record 17 Verify. Agent decides enrichment path, escalation, and Vapi threshold on its own. |
| **Idea** | CRM data decay costs sales teams 20-30% of prospecting time. This is a real, daily pain. |
| **Technical Implementation** | FastAPI async worker, Redis Streams SSE, webhooks, Akash LLM reasoning, Ghost Postgres persistence. |
| **Tool Use** | Redis, TinyFish, Vapi, Guild.ai — all producing visible artifacts during the demo. |
| **Demo** | Record 17 phone rings on stage. Confidence meter fills live. Guild.ai audit trail scrolls in real time. |
