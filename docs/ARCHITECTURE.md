# Architecture (as built)

```
uv run acme  ──►  cli.py (rich)  ──►  build_acme_assist()  ── create_agent(gemma, tools, middleware, context_schema=AcmeContext)
                                           │
              middleware: AuditLogMiddleware → StaffDetectionMiddleware → acme_system_prompt (dynamic) → forgiving_tools
                                           │
     ┌──────────── specialist tools (each one is its own create_agent) ────────────┐   shortcut tools
     orders · returns · catalog · stock · promos · account                          │   get_customer_profile
     hr · it · procurement · analytics · marketing · cs_desk                        │   track_shipment · issue_refund
     └──────────────────────────────── tools/*.py ──────────────────────────────────┘   escalate_to_human · search_policies
                                           │
                                   api.py (AcmeAPI) — HTTP, ACME_API_URL
                                           │
                    ACME Systems API (hosted: FastAPI + SQLite + simulation clock, policy KB)
                                           └── chaos modes (instructor-controlled, /admin)
```

## Request lifecycle

1. The CLI collects the user's identity (persona or `/login`) into an `AcmeContext` and calls
   `agent.stream(..., context=ctx, config={"configurable": {"thread_id": ...}})`.
2. `acme_system_prompt` builds the system prompt from `prompts/acme_assist.md` plus a "current session"
   block generated from the context.
3. The orchestrator model picks tools. A specialist tool runs a whole nested agent with only the `request`
   string it was given, and returns that agent's final message.
4. Tools call the ACME Systems API through `AcmeAPI`. Money is integer cents and timestamps are UTC.
5. `AuditLogMiddleware` appends every model step to `logs/audit-YYYYMMDD.log`.

## The ACME Systems API

- **Simulation clock:** data is generated relative to when the API was last started. Shipments progress in
  real time, and about 500 future orders become visible as their `placed_at` passes.
- **Chaos modes:** `/admin` (needs a token) turns on outages, slowness, flakiness, 429s, or read-only mode.
- Full endpoint list: open `$ACME_API_URL/docs`.

## Key data

| Entity | Count (seed 1987) | Notes |
|---|---|---|
| Products | 219 | 12 departments; `warranty_months`, `certifications`, `cost_cents` (internal) |
| Locations | 40 stores + 4 DCs | hours, lat/lon |
| Customers | ~2,440 | tiers Standard/Silver/Gold; some duplicates from a 2024 migration |
| Orders | ~9,500 (+500 future) | web orders have shipments; ~12% split shipments |
| Employees | ~430 | roles: associate, store_manager, hr, it, buyer, analyst, marketing, exec |
| Purchase orders | 420 | open POs exist for many SKUs |
