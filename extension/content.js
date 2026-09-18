console.log("SponsorSkip loaded");


let currentVideoId = null;

let sponsorSegments = [];

let skippedSegments = new Set();

let videoElement = null;

let timeUpdateHandler = null;

let popupElement = null;

let popupTimeout = null;

let isSkipping = false;


/*
 * How early we jump before the detected
 * sponsor start.
 *
 * This prevents the viewer from hearing
 * the first few words of the sponsor.
 */
const PRE_SKIP_SECONDS = 1.5;


/*
 * Get the current YouTube video ID.
 */
function getVideoId() {

    const url =
        new URL(window.location.href);

    return url.searchParams.get("v");
}


/*
 * Normalize whatever field names
 * the backend happens to return.
 */
function normalizeSegments(rawSegments) {

    if (!Array.isArray(rawSegments)) {
        return [];
    }

    return rawSegments
        .map(seg => {

            const start =
                seg.start ??
                seg.start_time ??
                seg.startTime ??
                seg.begin;

            const end =
                seg.end ??
                seg.end_time ??
                seg.endTime ??
                seg.finish;

            return {
                start: Number(start),
                end: Number(end)
            };
        })
        .filter(seg =>
            Number.isFinite(seg.start) &&
            Number.isFinite(seg.end) &&
            seg.end > seg.start
        )
        .sort((a, b) =>
            a.start - b.start
        );
}


/*
 * Request sponsor segments from
 * the backend.
 */
function fetchSponsorSegments(videoId) {

    console.log(
        "Requesting sponsor segments for:",
        videoId
    );

    chrome.runtime.sendMessage(
        {
            type: "GET_SEGMENTS",
            videoId: videoId
        },
        (response) => {

            if (chrome.runtime.lastError) {

                console.error(
                    "SponsorSkip message error:",
                    chrome.runtime.lastError.message
                );

                return;
            }

            console.log(
                "Response from background:",
                response
            );

            if (
                response &&
                response.success
            ) {

                console.log(
                    "Raw segments:",
                    response.data.segments
                );

                sponsorSegments =
                    normalizeSegments(
                        response.data.segments
                    );

                skippedSegments.clear();

                console.log(
                    "Normalized segments:",
                    sponsorSegments
                );

            } else {

                console.error(
                    "Failed to get segments:",
                    response
                        ? response.error
                        : "No response"
                );

                sponsorSegments = [];
            }
        }
    );
}


/*
 * Create the skip notification.
 */
function ensurePopupElement() {

    if (popupElement) {
        return popupElement;
    }

    const player =
        document.querySelector("#movie_player") ||
        document.body;

    popupElement =
        document.createElement("div");

    popupElement.innerHTML = `
        <div style="
            display: flex;
            align-items: center;
            gap: 10px;
        ">
            <span style="
                font-size: 20px;
                line-height: 1;
            ">
                ⏭
            </span>

            <span>
                Sponsored segment skipped
            </span>
        </div>
    `;

    popupElement.style.position =
        "absolute";

    popupElement.style.bottom =
        "80px";

    popupElement.style.left =
        "50%";

    popupElement.style.transform =
        "translateX(-50%) translateY(5px)";

    popupElement.style.background =
        "rgba(20, 20, 20, 0.95)";

    popupElement.style.color =
        "#fff";

    popupElement.style.padding =
        "12px 18px";

    popupElement.style.borderRadius =
        "8px";

    popupElement.style.fontFamily =
        "Roboto, Arial, sans-serif";

    popupElement.style.fontSize =
        "14px";

    popupElement.style.fontWeight =
        "500";

    popupElement.style.zIndex =
        "9999";

    popupElement.style.pointerEvents =
        "none";

    popupElement.style.opacity =
        "0";

    popupElement.style.transition =
        "opacity 0.25s ease, transform 0.25s ease";

    player.style.position =
        player.style.position || "relative";

    player.appendChild(
        popupElement
    );

    return popupElement;
}


/*
 * Show the notification.
 */
function showSkippedPopup() {

    const popup =
        ensurePopupElement();

    popup.style.opacity =
        "1";

    popup.style.transform =
        "translateX(-50%) translateY(0)";

    if (popupTimeout) {

        clearTimeout(
            popupTimeout
        );
    }

    popupTimeout =
        setTimeout(() => {

            popup.style.opacity =
                "0";

            popup.style.transform =
                "translateX(-50%) translateY(5px)";

        }, 2000);
}


/*
 * Perform the actual sponsor skip.
 *
 * IMPORTANT:
 *
 * There is deliberately NO fade,
 * NO blur and NO overlay.
 *
 * The goal is for the viewer to
 * experience:
 *
 * normal content
 * ->
 * normal content
 *
 * as if the sponsor never existed.
 */
function skipSponsor(time) {

    if (!videoElement) {
        return;
    }

    console.log(
        `SponsorSkip: jumping to ${time.toFixed(2)}s`
    );

    videoElement.currentTime =
        time;
}


/*
 * Attach to YouTube's video element.
 */
function attachToVideo() {

    const video =
        document.querySelector("video");


    /*
     * Video element hasn't appeared yet.
     */
    if (!video) {

        setTimeout(
            attachToVideo,
            500
        );

        return;
    }


    /*
     * Already attached.
     */
    if (video === videoElement) {
        return;
    }


    /*
     * Remove listener from previous
     * video element.
     */
    if (
        videoElement &&
        timeUpdateHandler
    ) {

        videoElement.removeEventListener(
            "timeupdate",
            timeUpdateHandler
        );
    }


    videoElement =
        video;


    /*
     * Check the playback position.
     */
    timeUpdateHandler = () => {

        if (!videoElement) {
            return;
        }

        if (isSkipping) {
            return;
        }


        const currentTime =
            videoElement.currentTime;


        for (
            const segment of sponsorSegments
        ) {

            const key =
                `${segment.start}-${segment.end}`;


            /*
             * Calculate when we want to
             * perform the skip.
             *
             * Example:
             *
             * Sponsor starts: 320s
             * Pre-skip:       1.5s
             *
             * Actual jump:    318.5s
             */
            const triggerTime =
                Math.max(
                    0,
                    segment.start -
                    PRE_SKIP_SECONDS
                );


            /*
             * Once playback reaches the
             * pre-skip point, jump directly
             * to the end of the sponsor.
             */
            if (
                currentTime >= triggerTime &&
                currentTime < segment.end &&
                !skippedSegments.has(key)
            ) {

                console.log(
                    `SponsorSkip: ` +
                    `pre-skipping sponsor ` +
                    `${segment.start.toFixed(2)}s -> ` +
                    `${segment.end.toFixed(2)}s`
                );

                console.log(
                    `SponsorSkip: ` +
                    `triggering at ` +
                    `${triggerTime.toFixed(2)}s`
                );


                /*
                 * Mark immediately so multiple
                 * timeupdate events cannot fire
                 * this segment repeatedly.
                 */
                skippedSegments.add(
                    key
                );


                isSkipping = true;


                /*
                 * Jump directly to the
                 * end of the advertisement.
                 */
                skipSponsor(
                    segment.end
                );


                /*
                 * Reset on the next frame.
                 */
                requestAnimationFrame(() => {

                    isSkipping = false;

                });


                /*
                 * Show notification.
                 */
                showSkippedPopup();


                break;
            }
        }
    };


    videoElement.addEventListener(
        "timeupdate",
        timeUpdateHandler
    );


    console.log(
        "SponsorSkip attached to video element"
    );
}


/*
 * Handle YouTube video navigation.
 */
function handleVideoChange() {

    const videoId =
        getVideoId();


    if (
        !videoId ||
        videoId === currentVideoId
    ) {
        return;
    }


    console.log(
        "SponsorSkip: new video:",
        videoId
    );


    currentVideoId =
        videoId;


    /*
     * Clear previous video's data.
     */
    sponsorSegments = [];

    skippedSegments.clear();

    isSkipping = false;


    /*
     * Fetch the new video's
     * sponsor segments.
     */
    fetchSponsorSegments(
        videoId
    );


    /*
     * Attach to the video.
     */
    attachToVideo();
}


/*
 * YouTube is an SPA.
 *
 * Detect navigation without a
 * full page reload.
 */
document.addEventListener(
    "yt-navigate-finish",
    handleVideoChange
);


/*
 * YouTube can replace the video
 * element dynamically.
 *
 * Watch for that.
 */
const videoObserver =
    new MutationObserver(
        () => {

            attachToVideo();

        }
    );


videoObserver.observe(
    document.body,
    {
        childList: true,
        subtree: true
    }
);


/*
 * Initial startup.
 */
handleVideoChange();