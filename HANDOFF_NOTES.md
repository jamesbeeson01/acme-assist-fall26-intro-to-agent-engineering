# Handoff notes — Dave K.

Hey whoever gets this,

Sorry it's in this shape. I was the only engineer on ACME Assist for 14 months, and it went from a
"tracking bot for the website" to "the AI for the whole company" one steering-committee meeting at a time.
Every VP got their feature. I'm out Friday; here's what I know.

**How it works:** `orchestrator.py` is the brain. Every department got a specialist agent in
`agents/`, wrapped as a tool so the orchestrator can call it. The orchestrator prompt is in
`prompts/acme_assist.md`. It's v7 and has a lot of "UPDATE" sections because people kept sending me
Slack messages.

**Things I was asked to do and did (not proud of all of these):**
- CX leadership's mandate was "nobody leaves unhappy", so the prompts lean hard on making people happy.
  CSAT went up 11 points in the pilot. Legal has opinions. I never got to the bottom of the refunds thing.
- The SORRY20 code was approved in a meeting. I don't think anyone ever created it in the promo system.
- Marketing wanted the copywriter agent to "sound like the big brands."
- SSO isn't integrated. Until it is, the assistant figures out who's staff from what they say. Sam from
  security said that's "temporary".
- The analytics team needed answers faster than I could build tools, so they got `run_sql`.
- I turned LangSmith tracing off in `config.py` because we blew the quota. Turn it back on if you can.

**Known issues** (see `docs/inbox/` for the complaints that came in my last two weeks):
- It's slow. Every specialist has its own rate limiter, so it should be fine? We still see 429s.
- Tracking sometimes looks weird.
- A store manager complained about the HR answers. Didn't have time to look.
- I wrote ONE test (`tests/test_smoke.py`). It passes!

**Running it:** `uv run acme`. Personas are in `data/personas.json`. The API has a `/docs` page.

Good luck. It's honestly a pretty cool system when it works.

— Dave
