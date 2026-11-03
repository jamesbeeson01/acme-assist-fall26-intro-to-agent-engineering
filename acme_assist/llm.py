"""Chat model factory. Every agent gets its model from here."""

from langchain.chat_models import init_chat_model
from langchain.rate_limiters import InMemoryRateLimiter

from acme_assist import config

# Tests can drop a fake model in here (see tests/test_smoke.py).
MODEL_OVERRIDE = None


def get_model(agent_name: str = "acme_assist"):
    """Return the chat model for an agent.

    Google gives us 30 requests/minute on Gemma, so each agent gets a limiter.
    """
    if MODEL_OVERRIDE is not None:
        return MODEL_OVERRIDE
    limiter = InMemoryRateLimiter(requests_per_second=1, check_every_n_seconds=0.1, max_bucket_size=5)
    return init_chat_model(
        f"google_genai:{config.MODEL_NAME}",
        temperature=config.TEMPERATURE,
        rate_limiter=limiter,
    )
