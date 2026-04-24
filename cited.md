# CRM Heal Agent Output

This file is prepared for hackathon submission.

## Sources and Actions

- Input dataset: `data/dirty_crm.csv`
- Redis or memory state: job hashes, queue, events
- TinyFish: configured or mock web enrichment
- Vapi: configured or mock voice verification
- Guild.ai: configured or local audit trace
- Ghost by TigerData: configured or skipped Postgres persistence

## Latest Demo Output

Run the app and export audit data from `GET /api/audit/{batch_id}` after a demo run.
