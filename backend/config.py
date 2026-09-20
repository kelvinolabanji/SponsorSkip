"""Environment configuration, loaded once from ``.env``."""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/sponsorskip"
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
