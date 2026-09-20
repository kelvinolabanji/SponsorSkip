# SponsorSkip

A Chrome extension that detects and skips sponsored segments in YouTube videos.

Unlike crowdsourced tools such as SponsorBlock, SponsorSkip needs no community timestamps. It reads the video's transcript and asks an LLM to find the sponsor reads, so it can work on videos nobody has annotated yet.

## Features

- **Auto skip:** jumps past a detected sponsor segment as soon as playback reaches it.
- **Manual skip:** shows a skip button during a sponsor segment and leaves the choice to you.
- **Mode switch:** toggle between the two modes from the extension popup. The setting is saved with `chrome.storage.sync`.
- **Non-blocking detection:** the video plays normally while detection runs, and segments are skipped as soon as they arrive.
- **Caching:** results are stored per video, so each video is analysed once.

## How it works

1. The extension detects the video you opened and asks the backend for its sponsor segments.
2. The backend returns them from the database if the video was analysed before.
3. Otherwise it downloads the video's captions with `yt-dlp` and cleans the transcript.
4. The transcript is split into overlapping windows, and each window is sent to an LLM.
5. The replies are validated, overlapping detections are merged, and the result is saved and returned.

The content script never calls the backend directly. It messages the background service worker, which makes the request. This is required in Manifest V3, and it also lets the worker cancel outdated requests when you switch videos.
