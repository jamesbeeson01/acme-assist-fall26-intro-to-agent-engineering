# ACME Assist

> **Class snapshot, Fall 2026.** This is the class's shared copy of ACME Assist for Intro to Agent
> Engineering. Every push to `main` redeploys the live agent the whole class is chatting with, so a bad
> push breaks it for everyone: fix it forward or `git revert` it. Not maintained after the term; it will be
> archived. The original student starter is `intro-to-agent-engineering-project-2-student`.

One assistant for everyone at ACME (A Company Making Everything): customers on acme.com and every
employee from the stockroom to the C-suite. It's built with LangChain `create_agent` on Google's Gemma
models, and it orchestrates 12 specialist agents over the ACME Systems API.

> **Status:** in production, unowned. The engineer who built it, Dave, has left.
> Start with [`HANDOFF_NOTES.md`](HANDOFF_NOTES.md), then your manager's note in
> [`docs/inbox/KICKOFF.md`](docs/inbox/KICKOFF.md).

## Quick start

You'll need [uv](https://docs.astral.sh/uv/) and a Google AI Studio API key.

```bash
uv sync
cp .env.example .env      # then put your keys and the API URL in .env
uv run acme               # chat in the terminal
```

ACME Assist talks to the **ACME Systems API**, which your instructor hosts. Set `ACME_API_URL` in `.env`
to the URL they give you. The API's interactive docs are at `$ACME_API_URL/docs`.

## What's in here

| Path | What it is |
|---|---|
| `acme_assist/orchestrator.py` | **ACME Assist**, the main agent: routing, shortcut tools, middleware |
| `acme_assist/agents/` | 12 specialist agents (orders, returns, catalog, stock, promos, account, hr, it, procurement, analytics, marketing, cs_desk) |
| `acme_assist/tools/` | Tools that call the ACME Systems API |
| `acme_assist/middleware.py` | Audit logging, staff detection, the dynamic system prompt, tool error handling |
| `acme_assist/prompts/acme_assist.md` | The orchestrator's system prompt |
| `acme_assist/cli.py` | The `rich` terminal client |
| `data/kb/` | Policy documents (returns, warranty, PTO, IT runbooks...) |
| `data/personas.json` | Demo customers and employees, used by the CLI login menu |
| `docs/` | Architecture, and the inbox: your manager's notes and the complaints about ACME Assist |
| `evals/` | Where your eval datasets and evaluators go |
| `acme_assist/server.py` | The HTTP server the class chat uses (see below) |
| `tests/` | pytest tests |

## Observability

The class shares one self-hosted Langfuse. Put `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and
`LANGFUSE_BASE_URL` in `.env` (your instructor shares them) and every turn becomes a trace. Set
`ACME_STUDENT` so your CLI traces show under your name; traces from the class chat already carry your
(de-identified) dashboard id, so filter by User in Langfuse to find your own. The CLI banner shows whether
tracing is on.

## The class deployment

The live agent runs on Railway from this repo's `main` (`railway.json`) as an HTTP server,
`acme_assist/server.py`, which the class dashboard's chat calls:

| Route | What it does |
|---|---|
| `POST /chat` `{student, text, thread_id?, persona?}` | One turn. No `thread_id` starts a conversation as `persona` |
| `GET /threads?student=` | That student's conversations, newest first |
| `GET /threads/<id>?student=` | One conversation's messages |
| `GET /personas` | The demo personas (`data/personas.json`) |

Conversations live in Postgres (`DATABASE_URL`) through LangGraph's `PostgresSaver`, so they survive
redeploys. Run it locally with `uv run uvicorn acme_assist.server:app --reload` (in memory without
`DATABASE_URL`, no auth without `CLASS_SPACE_TOKEN`).

## Rate limits

The Gemma free tier allows **30 requests per minute per API key**. One chat turn can easily make 4–10
model calls (orchestrator plus specialists).

## Troubleshooting

- *The assistant says it can't find anything:* check that the API is reachable, e.g.
  `curl $ACME_API_URL/health`.
- *Data looks different from yesterday:* it is. The API runs on a live clock: orders keep arriving and
  packages keep moving. Everyone in the class shares the same data, so other people's changes show up too.
