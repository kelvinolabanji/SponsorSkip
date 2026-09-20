"""Tunable constants for sponsor detection."""

# Model request
MODEL = "openai/gpt-oss-20b"
TEMPERATURE = 0
MAX_RESPONSE_TOKENS = 700  # keep responses small to avoid truncated JSON

# Transcript windowing (measured in characters)
WINDOW_SIZE = 5500
OVERLAP_SIZE = 1000
WINDOW_PAUSE_SECONDS = 1.0  # pause between windows to stay under the TPM limit

# Retries (delays grow linearly with the attempt number where noted)
MAX_RETRIES = 4
INVALID_JSON_BACKOFF_SECONDS = 1.5  # multiplied by the attempt number
API_ERROR_BACKOFF_SECONDS = 2  # multiplied by the attempt number
RATE_LIMIT_WAIT = 3  # used when the API gives no wait hint
RATE_LIMIT_MARGIN_SECONDS = 0.5  # added on top of the wait

# Segment validation and merging
SEGMENT_LABEL = "sponsor"
DEFAULT_REASON = "Sponsor segment detected."
MAX_REASON_LENGTH = 250
MAX_SEGMENT_SECONDS = 600  # longer "sponsor reads" are treated as model mistakes
MERGE_GAP_SECONDS = 8  # overlapping windows give slightly different boundaries
