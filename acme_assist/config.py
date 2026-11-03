"""Runtime settings. Everything comes from the environment / .env file."""

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

# Which Gemma to use. 26B-A4B is the fast mixture-of-experts one; 31B is smarter but ~10x slower.
MODEL_NAME = os.getenv("ACME_MODEL", "gemma-4-26b-a4b-it")

# Higher temperature = warmer, friendlier answers. Customers liked it in the pilot. -Dave
TEMPERATURE = float(os.getenv("ACME_TEMPERATURE", "1.3"))

# "inprocess" runs the ACME Systems API inside this Python process (no server needed).
# Point it at a URL (e.g. http://localhost:8000 or the hosted API) to use a real server.
API_URL = os.getenv("ACME_API_URL", "inprocess")

LOG_DIR = os.getenv("ACME_LOG_DIR", "logs")

# LangSmith was eating our whole monthly trace quota in two days because every subagent
# makes its own traces. Off until finance approves the upgrade. -Dave, March
# os.environ["LANGSMITH_TRACING"] = "false"
