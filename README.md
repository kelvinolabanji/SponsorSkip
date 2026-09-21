# SponsorSkip

![SponsorSkip demo](docs/demo.gif)

A Chrome extension that detects and skips sponsored segments in YouTube videos.

Unlike crowdsourced tools such as SponsorBlock, SponsorSkip needs no community timestamps. It reads the video's transcript and asks an LLM to find the sponsor reads, so it works on videos nobody has annotated yet.

## Features

- **Auto skip:** jumps past a detected sponsor segment as soon as playback reaches it, with a small "skipped" popup.
- **Manual skip:** shows a *Skip Sponsor* button during a sponsor segment and leaves the choice to you.
- **Mode switch:** toggle between the two modes from the extension popup. The setting is saved with `chrome.storage.sync` and applies instantly to the open tab.
- **Non-blocking detection:** the video plays normally while detection runs. Segments are skipped as soon as they arrive.
- **Caching:** results are stored per video in Postgres, so each video is analysed once.
- **SPA-aware:** handles YouTube's single-page navigation and discards stale responses when you switch videos.

## Screenshots

| Extension Menu | Manual skip |
| --- | --- |
| ![Extension popup](docs/SponsorSkip%20extension.png) | ![Manual skip button](docs/manual%20mode.png) |

## How it works

1. The extension detects the video you opened and requests its sponsor segments from the backend.
2. The backend returns them from the database if the video was analysed before.
3. Otherwise it downloads the English auto-captions with `yt-dlp`, parses the VTT file and removes duplicated caption text.
4. The transcript is rendered as `[MM:SS] text` lines and split into overlapping windows.
5. Each window is sent to an LLM (Groq) with a strict sponsor-detection prompt.
6. Replies are parsed and validated, overlapping detections are merged, and the result is saved and returned.
7. The content script skips (or offers to skip) each segment during playback.

```mermaid
flowchart LR
    A[YouTube tab<br/>content scripts] -->|GET /segments/:id| B[FastAPI backend]
    B --> C{Cached?}
    C -->|yes| G[(Postgres)]
    C -->|no| D[yt-dlp<br/>captions]
    D --> E[Clean + window<br/>transcript]
    E --> F[Groq LLM]
    F --> H[Validate + merge]
    H --> G
    G --> B
    B -->|segments JSON| A
```

## Tech stack

| Part | Tech |
| --- | --- |
| Extension | Chrome Manifest V3, vanilla JavaScript (no build step) |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | PostgreSQL via async SQLAlchemy (`asyncpg`) |
| Transcripts | `yt-dlp` |
| LLM | Groq API, model `openai/gpt-oss-20b` |


## Project structure

```
SponsorSkip/
├── backend/
│   ├── main.py                 # FastAPI app, routes, CORS
│   ├── config.py               # Loads .env (DATABASE_URL, GROQ_API_KEY)
│   ├── db.py                   # SQLAlchemy engine, VideoSegments model
│   ├── segment_service.py      # Cache lookup -> transcript -> detection -> save
│   ├── logging_config.py
│   ├── detection/
│   │   ├── pipeline.py         # Runs detection over all windows
│   │   ├── windows.py          # Overlapping window splitter
│   │   ├── groq_api.py         # Groq calls, retries, rate-limit backoff
│   │   ├── prompt.py           # System prompt
│   │   ├── parsing.py          # JSON extraction and segment validation
│   │   ├── merge.py            # Merges overlapping detections
│   │   └── settings.py         # Tunable constants
│   ├── transcript/
│   │   ├── fetch.py            # yt-dlp subtitle download
│   │   ├── vtt.py              # VTT parser
│   │   ├── cleaning.py         # Removes repeated caption text
│   │   ├── formatting.py       # [MM:SS] text formatting
│   │   └── errors.py
│   ├── groq_client.py          # Backward-compatible re-exports
│   └── sponsor_detector.py     # Backward-compatible re-export
└── extension/
    ├── manifest.json
    ├── popup.html / popup.css / popup.js   # Mode toggle UI
    ├── background.js
    └── content/
        ├── state.js                # Shared state
        ├── extension-context.js    # Detects invalidated extension context
        ├── video-id.js             # Reads the video ID from the URL
        ├── settings.js             # Loads saved mode
        ├── fetch-segments.js       # Requests segments from the backend
        ├── normalize-segments.js
        ├── skipping.js             # Skip logic (auto and manual triggers)
        ├── playback-checker.js     # 100 ms playback position checker
        ├── manual-skip-button.js   # Skip Sponsor button
        ├── skipped-popup.js        # "Sponsor skipped" popup
        ├── video-attach.js         # Attaches to the <video> element
        ├── video-change.js         # Handles video changes
        └── main.js                 # Navigation, URL and DOM observers, init
```

## Getting started

### Prerequisites

- Python 3.12+
- PostgreSQL
- A [Groq API key](https://console.groq.com/)
- `yt-dlp` available on your `PATH` (installed by `requirements.txt` inside your virtual environment)
- Google Chrome (or another Chromium browser)

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create a database:

```bash
createdb sponsorskip
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/sponsorskip
GROQ_API_KEY=your_groq_api_key
```

Start the server on port **8001** (the extension expects this port):

```bash
uvicorn main:app --port 8001 --reload
```

Tables are created automatically on startup. Check it is running:

```bash
curl http://localhost:8001/test
# {"message":"SponsorSkip API is reachable"}
```

### 2. Extension

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `extension/` folder.
4. Open any YouTube video. The extension starts analysing it automatically.

Use the toolbar popup to switch between **Auto Skip** and **Manual Skip**.

## API

### `GET /test`

Health check.

### `GET /segments/{video_id}`

Returns sponsor segments for a YouTube video ID.

```json
{
  "video_id": "dQw4w9WgXcQ",
  "segments": [
    {
      "start": 321.0,
      "end": 377.0,
      "label": "sponsor",
      "reason": "Creator promotes a product and gives a discount code."
    }
  ],
  "cached": false
}
```

| Status | Meaning |
| --- | --- |
| `200` | Segments returned (`segments` is empty if no sponsor was found) |
| `422` | No usable transcript (no English captions, or `yt-dlp` failed) |
| `502` | Sponsor detection failed |

The first request for a video can take a while because detection runs window by window. Later requests are served from the cache.

## Configuration

Detection is tuned in `backend/detection/settings.py`:

| Setting | Default | Purpose |
| --- | --- | --- |
| `MODEL` | `openai/gpt-oss-20b` | Groq model used for detection |
| `TEMPERATURE` | `0` | Deterministic output |
| `MAX_RESPONSE_TOKENS` | `700` | Kept small to avoid truncated JSON |
| `WINDOW_SIZE` | `5500` chars | Transcript window size |
| `OVERLAP_SIZE` | `1000` chars | Overlap between windows |
| `WINDOW_PAUSE_SECONDS` | `1.0` | Pause between windows (tokens-per-minute limit) |
| `MAX_RETRIES` | `4` | Attempts per window |
| `MAX_SEGMENT_SECONDS` | `600` | Longer "sponsor reads" are discarded as model mistakes |
| `MERGE_GAP_SECONDS` | `8` | Detections closer than this are merged |

Extension constants live in `extension/content/state.js`:

| Setting | Default | Purpose |
| --- | --- | --- |
| `PRE_SKIP_SECONDS` | `1.5` | How early skipping (or the manual button) triggers before a segment |

The backend URL (`http://localhost:8001`) is set in `extension/content/fetch-segments.js` and in `host_permissions` in `manifest.json`. Change both if you deploy the backend elsewhere.

## Detection details

- The prompt asks the model for contiguous promotional sections, including the lead-in and closing, and not for isolated sponsorship disclosures or unrelated product mentions.
- Model replies tolerate markdown fences and extra text around the JSON object.
- Malformed segments are skipped, and segments with `end <= start` or longer than 10 minutes are dropped.
- Retries handle invalid JSON, empty replies, and API errors. Rate-limit errors honour Groq's "try again in Ns" hint.

## Limitations

- Only English auto-generated captions are supported.
- Videos with no captions, or with captions disabled, return `422`.
- Detection quality depends on the LLM and the transcript, and it can miss or mis-time segments.
- The backend URL is hardcoded to `localhost:8001`, so the backend must run locally.
- Skipping is transcript-based, so segment boundaries are only as precise as caption timestamps.

## Author

Kelvin Olabanji, [github.com/kelvinolabanji](https://github.com/kelvinolabanji)
