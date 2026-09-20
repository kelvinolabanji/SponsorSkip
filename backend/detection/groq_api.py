"""Send transcript windows to Groq, with retries."""

import logging
import re
import time

from groq import Groq

from config import GROQ_API_KEY
from detection.parsing import extract_json, validate_segments
from detection.prompt import SYSTEM_PROMPT
from detection.settings import (
    API_ERROR_BACKOFF_SECONDS,
    INVALID_JSON_BACKOFF_SECONDS,
    MAX_RESPONSE_TOKENS,
    MAX_RETRIES,
    MODEL,
    RATE_LIMIT_MARGIN_SECONDS,
    RATE_LIMIT_WAIT,
    TEMPERATURE,
)

logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)

_USER_MESSAGE_PREFIX = "Analyze this transcript window for sponsor segments.\n\n"
_RATE_LIMIT_MARKERS = ("429", "rate_limit_exceeded", "Rate limit")
_RATE_LIMIT_HINT = re.compile(r"Please try again in ([0-9.]+)s")


def call_groq(transcript_window: str) -> list[dict]:
    """Detect sponsor segments in one transcript window.

    Retries on invalid JSON, empty or truncated replies, rate limits and other
    API errors. After ``MAX_RETRIES`` failed attempts it gives up and returns
    an empty list.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("Sending window to Groq (attempt %d/%d)", attempt, MAX_RETRIES)

        try:
            content = _request_completion(transcript_window)
        except Exception as error:  # any API failure is treated as retryable
            logger.warning("Groq request failed: %s", error)
            delay = _delay_after_api_error(error, attempt)
        else:
            try:
                segments = validate_segments(extract_json(content))
            except ValueError as error:
                logger.warning(
                    "Groq returned invalid JSON (%s). Raw response: %s", error, content
                )
                delay = INVALID_JSON_BACKOFF_SECONDS * attempt
            else:
                logger.info("Groq detected %d sponsor(s) in this window", len(segments))
                return segments

        if attempt < MAX_RETRIES:
            logger.info("Retrying in %.1fs", delay)
            time.sleep(delay)

    logger.error("Groq failed after %d attempts; returning no segments", MAX_RETRIES)
    return []


def _request_completion(transcript_window: str) -> str:
    """Make one chat completion request and return the reply text."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _USER_MESSAGE_PREFIX + transcript_window},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_RESPONSE_TOKENS,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Groq returned an empty response.")
    return content


def _delay_after_api_error(error: Exception, attempt: int) -> float:
    """Seconds to wait before retrying after a failed request."""
    error_text = str(error)
    if any(marker in error_text for marker in _RATE_LIMIT_MARKERS):
        return _rate_limit_delay(error_text)
    return API_ERROR_BACKOFF_SECONDS * attempt


def _rate_limit_delay(error_text: str) -> float:
    """Wait time for a rate-limit error: Groq's hint if present, plus a margin."""
    wait = RATE_LIMIT_WAIT

    hint = _RATE_LIMIT_HINT.search(error_text)
    if hint:
        try:
            wait = float(hint.group(1))
        except ValueError:
            pass

    return wait + RATE_LIMIT_MARGIN_SECONDS
