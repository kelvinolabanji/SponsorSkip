console.log("SponsorSkip loaded");

let currentVideoId = null;
let sponsorSegments = [];
let skippedSegments = new Set();
let videoElement = null;
let timeUpdateHandler = null;
let popupElement = null;
let popupTimeout = null;

function getVideoId() {
    const url = new URL(window.location.href);
    return url.searchParams.get("v");
}

// Handles whichever field names gemini_client.py actually returns
function normalizeSegments(rawSegments) {
    if (!Array.isArray(rawSegments)) return [];
    return rawSegments
        .map(seg => {
            const start = seg.start ?? seg.start_time ?? seg.startTime ?? seg.begin;
            const end = seg.end ?? seg.end_time ?? seg.endTime ?? seg.finish;
            return { start: Number(start), end: Number(end) };
        })
        .filter(seg => Number.isFinite(seg.start) && Number.isFinite(seg.end) && seg.end > seg.start);
}

function fetchSponsorSegments(videoId) {
    console.log("Requesting sponsor segments for:", videoId);

    chrome.runtime.sendMessage(
        { type: "GET_SEGMENTS", videoId: videoId },
        (response) => {
            if (chrome.runtime.lastError) {
                console.error("SponsorSkip message error:", chrome.runtime.lastError.message);
                return;
            }

            console.log("Response from background:", response);

            if (response.success) {
                console.log("Raw segments:", response.data.segments);
                sponsorSegments = normalizeSegments(response.data.segments);
                skippedSegments.clear();
                console.log("Normalized segments:", sponsorSegments);
            } else {
                console.error("Failed to get segments:", response.error);
                sponsorSegments = [];
            }
        }
    );
}

function ensurePopupElement() {
    if (popupElement) return popupElement;

    const player = document.querySelector("#movie_player") || document.body;

    popupElement = document.createElement("div");
    popupElement.textContent = "Sponsor skipped";
    popupElement.style.position = "absolute";
    popupElement.style.bottom = "70px";
    popupElement.style.left = "50%";
    popupElement.style.transform = "translateX(-50%)";
    popupElement.style.background = "rgba(28, 28, 28, 0.9)";
    popupElement.style.color = "#fff";
    popupElement.style.padding = "8px 16px";
    popupElement.style.borderRadius = "18px";
    popupElement.style.fontFamily = "Roboto, Arial, sans-serif";
    popupElement.style.fontSize = "14px";
    popupElement.style.fontWeight = "500";
    popupElement.style.zIndex = "9999";
    popupElement.style.pointerEvents = "none";
    popupElement.style.opacity = "0";
    popupElement.style.transition = "opacity 0.2s ease";

    player.style.position = player.style.position || "relative";
    player.appendChild(popupElement);

    return popupElement;
}

function showSkippedPopup() {
    const popup = ensurePopupElement();

    popup.style.opacity = "1";

    if (popupTimeout) clearTimeout(popupTimeout);
    popupTimeout = setTimeout(() => {
        popup.style.opacity = "0";
    }, 1500);
}

function attachToVideo() {
    const video = document.querySelector("video");

    if (!video) {
        setTimeout(attachToVideo, 500);
        return;
    }

    if (video === videoElement) return;

    if (videoElement && timeUpdateHandler) {
        videoElement.removeEventListener("timeupdate", timeUpdateHandler);
    }

    videoElement = video;

    timeUpdateHandler = () => {
        const t = videoElement.currentTime;

        for (const segment of sponsorSegments) {
            const key = `${segment.start}-${segment.end}`;

            if (t >= segment.start && t < segment.end && !skippedSegments.has(key)) {
                console.log(`SponsorSkip: skipping ${segment.start}s -> ${segment.end}s`);
                videoElement.currentTime = segment.end;
                skippedSegments.add(key);
                showSkippedPopup();
            }
        }
    };

    videoElement.addEventListener("timeupdate", timeUpdateHandler);
    console.log("SponsorSkip attached to video element");
}

function handleVideoChange() {
    const videoId = getVideoId();

    if (!videoId || videoId === currentVideoId) return;

    currentVideoId = videoId;
    sponsorSegments = [];
    skippedSegments.clear();

    fetchSponsorSegments(videoId);
    attachToVideo();
}

// YouTube is an SPA — this fires on in-app navigation between videos
document.addEventListener("yt-navigate-finish", handleVideoChange);

// YouTube sometimes replaces the <video> element; catch that too
const videoObserver = new MutationObserver(() => attachToVideo());
videoObserver.observe(document.body, { childList: true, subtree: true });

// Initial load
handleVideoChange();