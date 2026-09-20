/*
 * =========================================================
 * SponsorSkip - YouTube Content Script
 * =========================================================
 *
 * Handles:
 *
 * - YouTube video detection
 * - Sponsor segment requests
 * - First-play sponsor detection gate
 * - Automatic sponsor skipping
 * - Manual sponsor skipping
 * - Skip notifications
 * - YouTube SPA navigation
 * - Stale-response protection
 * - Extension context protection
 *
 */


/*
 * =========================================================
 * STARTUP
 * =========================================================
 */

console.log(
    "SponsorSkip content script loaded"
);


/*
 * =========================================================
 * STATE
 * =========================================================
 */

let currentVideoId = null;
let requestVideoId = null;
let sponsorSegments = [];
let skippedSegments = new Set();

let videoElement = null;
let timeUpdateHandler = null;

let popupElement = null;
let popupTimeout = null;

let isSkipping = false;
let autoSkip = true;

let manualSkipButton = null;
let activeManualSegment = null;

let playbackCheckInterval = null;


/*
 * =========================================================
 * FIRST-PLAY DETECTION GATE STATE
 * =========================================================
 *
 * When a video has no sponsor data yet, SponsorSkip needs
 * time to fetch the transcript and run sponsor detection.
 *
 * Without this gate, the video can reach a sponsor before
 * Groq has finished analysing the video.
 *
 * The gate temporarily pauses playback while detection
 * is running.
 *
 */

let detectionInProgress = false;
let detectionVideoId = null;
let resumeAfterDetection = false;
let detectionPlayHandler = null;

let detectionOverlay = null;


/*
 * Used to invalidate old navigation/request cycles.
 *
 * Every time the user navigates to another YouTube page,
 * this number increases.
 *
 * Old callbacks can then safely detect that they belong
 * to an outdated navigation cycle.
 */

let navigationGeneration = 0;


/*
 * Prevents the old content script from continuing to do
 * unnecessary work after the extension context disappears.
 */

let extensionContextInvalidated = false;


/*
 * =========================================================
 * CONFIGURATION
 * =========================================================
 */

const PRE_SKIP_SECONDS = 1.5;


/*
 * =========================================================
 * SAFE EXTENSION CONTEXT CHECK
 * =========================================================
 */

function isExtensionContextValid() {

    if (
        extensionContextInvalidated
    ) {
        return false;
    }

    try {

        const id =
            chrome.runtime.id;

        return Boolean(id);

    } catch (error) {

        extensionContextInvalidated =
            true;

        return false;
    }
}


/*
 * =========================================================
 * SAFE RUNTIME MESSAGE
 * =========================================================
 */

function safeSendMessage(
    message,
    callback
) {

    if (
        !isExtensionContextValid()
    ) {
        return false;
    }

    try {

        chrome.runtime.sendMessage(
            message,
            (response) => {

                try {

                    if (
                        chrome.runtime.lastError
                    ) {

                        if (
                            typeof callback ===
                            "function"
                        ) {

                            callback(
                                null,
                                chrome.runtime.lastError
                            );
                        }

                        return;
                    }

                } catch (error) {

                    extensionContextInvalidated =
                        true;

                    return;
                }


                if (
                    typeof callback ===
                    "function"
                ) {

                    callback(
                        response,
                        null
                    );
                }
            }
        );

        return true;

    } catch (error) {

        if (
            error &&
            typeof error.message ===
            "string" &&
            error.message.includes(
                "Extension context invalidated"
            )
        ) {

            extensionContextInvalidated =
                true;

            return false;
        }

        console.log(
            "SponsorSkip: runtime message could not be sent.",
            error
        );

        return false;
    }
}


/*
 * =========================================================
 * GET CURRENT VIDEO ID
 * =========================================================
 */

function getVideoId() {

    try {

        const url =
            new URL(
                window.location.href
            );

        /*
         * Only use the actual YouTube "v"
         * query parameter.
         */

        return url.searchParams.get(
            "v"
        );

    } catch (error) {

        console.log(
            "SponsorSkip: failed to read video ID.",
            error
        );

        return null;
    }
}


/*
 * =========================================================
 * LOAD SETTINGS
 * =========================================================
 */

function loadSettings() {

    if (
        !isExtensionContextValid()
    ) {
        return;
    }

    try {

        chrome.storage.sync.get(
            {
                autoSkip: true
            },
            (settings) => {

                /*
                 * The extension may have been invalidated
                 * while storage was being read.
                 */

                if (
                    !isExtensionContextValid()
                ) {
                    return;
                }

                try {

                    if (
                        chrome.runtime.lastError
                    ) {

                        console.log(
                            "SponsorSkip: could not load settings."
                        );

                        return;
                    }

                } catch (error) {

                    extensionContextInvalidated =
                        true;

                    return;
                }


                autoSkip =
                    settings.autoSkip;


                console.log(
                    "SponsorSkip mode:",
                    autoSkip
                        ? "Auto Skip"
                        : "Manual Skip"
                );


                updateManualSkipButton();
            }
        );

    } catch (error) {

        if (
            error &&
            typeof error.message ===
            "string" &&
            error.message.includes(
                "Extension context invalidated"
            )
        ) {

            extensionContextInvalidated =
                true;

            return;
        }

        console.log(
            "SponsorSkip: settings error.",
            error
        );
    }
}


/*
 * =========================================================
 * NORMALIZE SEGMENTS
 * =========================================================
 */

function normalizeSegments(
    segments
) {

    if (
        !Array.isArray(
            segments
        )
    ) {
        return [];
    }


    return segments

        .map(
            segment => {

                return {

                    start:
                        Number(
                            segment.start
                        ),

                    end:
                        Number(
                            segment.end
                        )
                };
            }
        )

        .filter(
            segment => {

                return (

                    Number.isFinite(
                        segment.start
                    ) &&

                    Number.isFinite(
                        segment.end
                    ) &&

                    segment.end >
                    segment.start
                );
            }
        )

        .sort(
            (a, b) =>
                a.start - b.start
        );
}


/*
 * =========================================================
 * DETECTION LOADING OVERLAY
 * =========================================================
 *
 * This appears inside the YouTube player while SponsorSkip
 * is analysing a brand-new video.
 *
 */

function showDetectionOverlay() {

    /*
     * Remove an existing overlay first.
     */

    if (
        detectionOverlay
    ) {

        detectionOverlay.remove();

        detectionOverlay =
            null;
    }


    const player =
        document.querySelector(
            "#movie_player"
        );


    if (
        !player
    ) {

        return;
    }


    /*
     * Make sure the player can contain
     * an absolutely positioned overlay.
     */

    if (
        getComputedStyle(player).position ===
        "static"
    ) {

        player.style.position =
            "relative";
    }


    detectionOverlay =
        document.createElement(
            "div"
        );


    detectionOverlay.className =
        "sponsorskip-detection-overlay";


    detectionOverlay.innerHTML = `
        <div class="sponsorskip-detection-card">

            <div class="sponsorskip-detection-logo">
                S
            </div>

            <div class="sponsorskip-detection-title">
                SponsorSkip
            </div>

            <div class="sponsorskip-detection-subtitle">
                Detecting sponsors...
            </div>

            <div class="sponsorskip-detection-spinner">
            </div>

        </div>
    `;


    Object.assign(
        detectionOverlay.style,
        {
            position:
                "absolute",

            inset:
                "0",

            zIndex:
                "2147483645",

            display:
                "flex",

            alignItems:
                "center",

            justifyContent:
                "center",

            background:
                "rgba(0, 0, 0, 0.28)",

            pointerEvents:
                "none",

            boxSizing:
                "border-box",

            fontFamily:
                "Arial, Helvetica, sans-serif"
        }
    );


    const card =
        detectionOverlay.querySelector(
            ".sponsorskip-detection-card"
        );


    Object.assign(
        card.style,
        {
            display:
                "flex",

            flexDirection:
                "column",

            alignItems:
                "center",

            justifyContent:
                "center",

            padding:
                "22px 28px",

            minWidth:
                "190px",

            background:
                "rgba(15, 15, 15, 0.94)",

            border:
                "1px solid rgba(255, 255, 255, 0.12)",

            borderRadius:
                "14px",

            boxShadow:
                "0 10px 40px rgba(0, 0, 0, 0.5)",

            color:
                "#ffffff",

            boxSizing:
                "border-box"
        }
    );


    const logo =
        detectionOverlay.querySelector(
            ".sponsorskip-detection-logo"
        );


    Object.assign(
        logo.style,
        {
            width:
                "38px",

            height:
                "38px",

            borderRadius:
                "10px",

            display:
                "flex",

            alignItems:
                "center",

            justifyContent:
                "center",

            background:
                "#ff0033",

            color:
                "#ffffff",

            fontSize:
                "20px",

            fontWeight:
                "700",

            marginBottom:
                "10px"
        }
    );


    const title =
        detectionOverlay.querySelector(
            ".sponsorskip-detection-title"
        );


    Object.assign(
        title.style,
        {
            fontSize:
                "15px",

            fontWeight:
                "600",

            lineHeight:
                "20px"
        }
    );


    const subtitle =
        detectionOverlay.querySelector(
            ".sponsorskip-detection-subtitle"
        );


    Object.assign(
        subtitle.style,
        {
            marginTop:
                "3px",

            fontSize:
                "12px",

            color:
                "rgba(255, 255, 255, 0.62)",

            lineHeight:
                "17px"
        }
    );


    const spinner =
        detectionOverlay.querySelector(
            ".sponsorskip-detection-spinner"
        );


    Object.assign(
        spinner.style,
        {
            width:
                "18px",

            height:
                "18px",

            marginTop:
                "13px",

            border:
                "2px solid rgba(255, 255, 255, 0.2)",

            borderTopColor:
                "#ff0033",

            borderRadius:
                "50%",

            animation:
                "sponsorskip-spin 0.8s linear infinite"
        }
    );


    /*
     * Add the spinner animation once.
     */

    if (
        !document.getElementById(
            "sponsorskip-detection-style"
        )
    ) {

        const style =
            document.createElement(
                "style"
            );


        style.id =
            "sponsorskip-detection-style";


        style.textContent = `
            @keyframes sponsorskip-spin {
                from {
                    transform: rotate(0deg);
                }

                to {
                    transform: rotate(360deg);
                }
            }
        `;


        document.head.appendChild(
            style
        );
    }


    player.appendChild(
        detectionOverlay
    );
}


/*
 * =========================================================
 * HIDE DETECTION OVERLAY
 * =========================================================
 */

function hideDetectionOverlay() {

    if (
        detectionOverlay
    ) {

        detectionOverlay.remove();

        detectionOverlay =
            null;
    }
}


/*
 * =========================================================
 * START DETECTION GATE
 * =========================================================
 */

function startDetectionGate(
    videoId
) {

    detectionInProgress =
        true;

    detectionVideoId =
        videoId;

    resumeAfterDetection =
        false;


    console.log(
        "SponsorSkip: first-play detection gate started for:",
        videoId
    );


    showDetectionOverlay();


    /*
     * If the video is already playing, pause it immediately.
     */

    if (
        videoElement &&
        !videoElement.paused &&
        !videoElement.ended
    ) {

        resumeAfterDetection =
            true;


        console.log(
            "SponsorSkip: pausing playback while sponsors are detected."
        );


        videoElement.pause();
    }


    /*
     * If the user tries to press Play while detection is
     * still running, immediately pause it again.
     *
     * This prevents the sponsor from playing while analysis
     * is still in progress.
     */

    if (
        videoElement
    ) {

        attachDetectionPlayHandler(
            videoElement
        );
    }
}


/*
 * =========================================================
 * DETECTION PLAY HANDLER
 * =========================================================
 */

function attachDetectionPlayHandler(
    video
) {

    if (
        detectionPlayHandler
    ) {

        try {

            video.removeEventListener(
                "play",
                detectionPlayHandler
            );

        } catch (error) {
            /*
             * Ignore old video errors.
             */
        }
    }


    detectionPlayHandler =
        () => {

            if (
                !detectionInProgress
            ) {
                return;
            }


            if (
                detectionVideoId !==
                currentVideoId
            ) {
                return;
            }


            /*
             * The user attempted to play before detection
             * finished.
             *
             * Pause it again.
             */

            resumeAfterDetection =
                true;


            console.log(
                "SponsorSkip: playback blocked until sponsor detection finishes."
            );


            try {

                video.pause();

            } catch (error) {

                console.log(
                    "SponsorSkip: could not pause during detection."
                );
            }
        };


    video.addEventListener(
        "play",
        detectionPlayHandler
    );
}


/*
 * =========================================================
 * FINISH DETECTION GATE
 * ========================================================= */

function finishDetectionGate(
    videoId
) {

    /*
     * Ignore a stale detection result.
     */

    if (
        detectionVideoId !==
        videoId
    ) {

        return;
    }


    const shouldResume =
        resumeAfterDetection;


    detectionInProgress =
        false;

    detectionVideoId =
        null;

    resumeAfterDetection =
        false;


    hideDetectionOverlay();


    /*
     * Remove the play handler.
     */

    if (
        videoElement &&
        detectionPlayHandler
    ) {

        try {

            videoElement.removeEventListener(
                "play",
                detectionPlayHandler
            );

        } catch (error) {

            /*
             * Ignore old video errors.
             */
        }
    }


    detectionPlayHandler =
        null;


    /*
     * Resume only if the video was actually playing
     * before detection started or the user attempted to
     * play it while detection was running.
     */

    if (
        shouldResume &&
        videoElement &&
        !videoElement.ended
    ) {

        console.log(
            "SponsorSkip: sponsor detection finished. Resuming playback."
        );


        try {

            const playPromise =
                videoElement.play();


            if (
                playPromise &&
                typeof playPromise.catch ===
                "function"
            ) {

                playPromise.catch(
                    error => {

                        console.log(
                            "SponsorSkip: could not resume playback automatically.",
                            error
                        );
                    }
                );
            }

        } catch (error) {

            console.log(
                "SponsorSkip: could not resume playback.",
                error
            );
        }
    }
}


/*
 * =========================================================
 * FETCH SPONSOR SEGMENTS
 * =========================================================
 *
 * This request goes directly from the content script
 * to the local FastAPI server.
 *
 */

function fetchSponsorSegments(
    videoId,
    generation
) {

    /*
     * Ignore requests belonging to an old navigation cycle.
     */

    if (
        generation !==
        navigationGeneration
    ) {

        console.log(
            "SponsorSkip: ignoring outdated request:",
            videoId
        );

        return;
    }


    console.log(
        "SponsorSkip: requesting sponsor segments for:",
        videoId
    );


    requestVideoId =
        videoId;


    fetch(
        `http://localhost:8001/segments/${encodeURIComponent(videoId)}`
    )

        .then(
            response => {

                console.log(
                    "SponsorSkip: API HTTP status:",
                    response.status
                );


                if (
                    !response.ok
                ) {

                    throw new Error(
                        `HTTP ${response.status}`
                    );
                }


                return response.json();
            }
        )

        .then(
            data => {

                /*
                 * Ignore responses from old navigation cycles.
                 */

                if (
                    generation !==
                    navigationGeneration
                ) {

                    console.log(
                        "SponsorSkip: ignoring stale response:",
                        videoId
                    );

                    return;
                }


                /*
                 * Ignore responses that no longer match
                 * the active request.
                 */

                if (
                    requestVideoId !==
                    videoId
                ) {

                    console.log(
                        "SponsorSkip: ignoring stale response:",
                        videoId
                    );

                    return;
                }


                /*
                 * Ignore responses for another video.
                 */

                if (
                    currentVideoId !==
                    videoId
                ) {

                    console.log(
                        "SponsorSkip: ignoring response because video changed:",
                        videoId
                    );

                    return;
                }


                /*
                 * Extra backend video-ID protection.
                 */

                if (
                    data &&
                    data.video_id &&
                    data.video_id !==
                    videoId
                ) {

                    console.log(
                        "SponsorSkip: backend returned data for a different video. Ignoring."
                    );

                    finishDetectionGate(
                        videoId
                    );

                    return;
                }


                /*
                 * Store the real sponsor segments.
                 */

                sponsorSegments =
                    normalizeSegments(
                        data &&
                        Array.isArray(
                            data.segments
                        )
                            ? data.segments
                            : []
                    );


                skippedSegments.clear();


                console.log(
                    "SponsorSkip: sponsor segments received for:",
                    videoId
                );


                console.log(
                    "Sponsor segments:",
                    sponsorSegments
                );


                /*
                 * =================================================
                 * RELEASE FIRST-PLAY DETECTION GATE
                 * =================================================
                 *
                 * The sponsor data is now available.
                 *
                 * Release the video BEFORE checking the sponsor
                 * position so the normal playback state is restored.
                 */

                finishDetectionGate(
                    videoId
                );


                /*
                 * Check immediately.
                 *
                 * This handles cached/fast responses and also
                 * protects against a sponsor that begins very
                 * close to the current playback position.
                 */

                checkSponsorPosition();


                /*
                 * Update the manual-skip UI after the segments
                 * have been loaded.
                 */

                updateManualSkipButton();
            }
        )

        .catch(
            error => {

                /*
                 * Ignore errors from stale requests.
                 */

                if (
                    generation !==
                    navigationGeneration ||
                    requestVideoId !==
                    videoId
                ) {

                    return;
                }


                console.log(
                    "SponsorSkip: failed to get segments:",
                    error
                );


                sponsorSegments =
                    [];


                hideManualSkipButton();


                /*
                 * IMPORTANT:
                 *
                 * Never leave the user permanently stuck on
                 * the detection screen because of an API error.
                 *
                 * Release the gate and allow playback.
                 */

                finishDetectionGate(
                    videoId
                );
            }
        );
}


/*
 * =========================================================
 * SHOW SKIPPED POPUP
 * =========================================================
 */

function showSkippedPopup() {

    /*
     * Remove an existing popup first.
     */

    if (
        popupElement
    ) {

        popupElement.remove();

        popupElement =
            null;
    }


    /*
     * Clear an existing timeout.
     */

    if (
        popupTimeout
    ) {

        clearTimeout(
            popupTimeout
        );

        popupTimeout =
            null;
    }


    /*
     * Find the actual YouTube player.
     */

    const player =
        document.querySelector(
            "#movie_player"
        );


    /*
     * If the player is not currently available,
     * do not create a floating body popup.
     */

    if (
        !player
    ) {

        console.log(
            "SponsorSkip: YouTube player not available for popup."
        );

        return;
    }


    /*
     * Make sure the player can contain an
     * absolutely positioned child.
     */

    if (
        getComputedStyle(player).position ===
        "static"
    ) {

        player.style.position =
            "relative";
    }


    /*
     * Create popup.
     */

    popupElement =
        document.createElement(
            "div"
        );


    popupElement.className =
        "sponsorskip-popup";


    popupElement.innerHTML = `
        <div class="sponsorskip-popup-icon">
            ✓
        </div>

        <div class="sponsorskip-popup-content">

            <div class="sponsorskip-popup-title">
                Sponsor skipped
            </div>

            <div class="sponsorskip-popup-subtitle">
                Sponsored segment removed
            </div>

        </div>
    `;


    /*
     * Popup styling.
     */

    Object.assign(
        popupElement.style,
        {
            position: "absolute",

            right: "24px",

            bottom: "75px",

            zIndex: "2147483647",

            display: "flex",

            alignItems: "center",

            gap: "12px",

            padding: "12px 16px",

            background:
                "rgba(15, 15, 15, 0.96)",

            border:
                "1px solid rgba(255, 255, 255, 0.12)",

            borderRadius: "12px",

            boxShadow:
                "0 8px 30px rgba(0, 0, 0, 0.45)",

            color: "#ffffff",

            fontFamily:
                "Arial, Helvetica, sans-serif",

            opacity: "0",

            transform:
                "translateY(10px)",

            transition:
                "opacity 0.2s ease, transform 0.2s ease",

            pointerEvents:
                "none",

            boxSizing:
                "border-box",

            whiteSpace:
                "nowrap"
        }
    );


    /*
     * Popup icon.
     */

    const icon =
        popupElement.querySelector(
            ".sponsorskip-popup-icon"
        );


    Object.assign(
        icon.style,
        {
            width: "28px",

            height: "28px",

            borderRadius: "50%",

            display: "flex",

            alignItems: "center",

            justifyContent: "center",

            background:
                "#ff0033",

            color:
                "#ffffff",

            fontSize:
                "15px",

            fontWeight:
                "700",

            flexShrink:
                "0"
        }
    );


    /*
     * Popup text container.
     */

    const content =
        popupElement.querySelector(
            ".sponsorskip-popup-content"
        );


    Object.assign(
        content.style,
        {
            display:
                "flex",

            flexDirection:
                "column",

            gap:
                "2px"
        }
    );


    /*
     * Popup title.
     */

    const title =
        popupElement.querySelector(
            ".sponsorskip-popup-title"
        );


    Object.assign(
        title.style,
        {
            fontSize:
                "14px",

            fontWeight:
                "600",

            lineHeight:
                "18px"
        }
    );


    /*
     * Popup subtitle.
     */

    const subtitle =
        popupElement.querySelector(
            ".sponsorskip-popup-subtitle"
        );


    Object.assign(
        subtitle.style,
        {
            fontSize:
                "12px",

            color:
                "rgba(255, 255, 255, 0.62)",

            lineHeight:
                "16px"
        }
    );


    /*
     * Append to the YouTube PLAYER,
     * not document.body.
     */

    player.appendChild(
        popupElement
    );


    /*
     * Trigger the entrance animation.
     */

    requestAnimationFrame(
        () => {

            if (
                !popupElement
            ) {
                return;
            }


            popupElement.style.opacity =
                "1";


            popupElement.style.transform =
                "translateY(0)";
        }
    );


    /*
     * Keep the popup visible for 2.2 seconds.
     */

    popupTimeout =
        setTimeout(
            () => {

                if (
                    !popupElement
                ) {
                    return;
                }


                popupElement.style.opacity =
                    "0";


                popupElement.style.transform =
                    "translateY(10px)";


                setTimeout(
                    () => {

                        if (
                            popupElement
                        ) {

                            popupElement.remove();

                            popupElement =
                                null;
                        }

                    },
                    220
                );

            },
            2200
        );
}


/*
 * =========================================================
 * CREATE MANUAL SKIP BUTTON
 * =========================================================
 */

function createManualSkipButton() {

    if (
        manualSkipButton
    ) {
        return;
    }


    manualSkipButton =
        document.createElement(
            "button"
        );


    manualSkipButton.type =
        "button";


    manualSkipButton.innerHTML =
        "⏭ Skip Sponsor";


    manualSkipButton.className =
        "sponsorskip-manual-button";


    Object.assign(
        manualSkipButton.style,
        {
            position:
                "absolute",

            right:
                "20px",

            bottom:
                "65px",

            zIndex:
                "2147483646",

            display:
                "none",

            alignItems:
                "center",

            justifyContent:
                "center",

            gap:
                "8px",

            padding:
                "10px 15px",

            border:
                "1px solid rgba(255, 255, 255, 0.16)",

            borderRadius:
                "10px",

            background:
                "rgba(20, 20, 20, 0.94)",

            color:
                "#ffffff",

            fontFamily:
                "Arial, Helvetica, sans-serif",

            fontSize:
                "13px",

            fontWeight:
                "600",

            lineHeight:
                "18px",

            cursor:
                "pointer",

            boxShadow:
                "0 6px 24px rgba(0, 0, 0, 0.4)",

            backdropFilter:
                "blur(10px)",

            WebkitBackdropFilter:
                "blur(10px)",

            transition:
                "background 0.15s ease, transform 0.15s ease, border-color 0.15s ease"
        }
    );


    /*
     * Hover state.
     */

    manualSkipButton.addEventListener(
        "mouseenter",
        () => {

            if (
                !manualSkipButton
            ) {
                return;
            }


            manualSkipButton.style.background =
                "#ff0033";


            manualSkipButton.style.borderColor =
                "#ff0033";


            manualSkipButton.style.transform =
                "translateY(-1px)";
        }
    );


    manualSkipButton.addEventListener(
        "mouseleave",
        () => {

            if (
                !manualSkipButton
            ) {
                return;
            }


            manualSkipButton.style.background =
                "rgba(20, 20, 20, 0.94)";


            manualSkipButton.style.borderColor =
                "rgba(255, 255, 255, 0.16)";


            manualSkipButton.style.transform =
                "translateY(0)";
        }
    );


    /*
     * Manual skip click.
     */

    manualSkipButton.addEventListener(
        "click",
        (event) => {

            event.preventDefault();

            event.stopPropagation();


            if (
                !activeManualSegment
            ) {
                return;
            }


            const segment =
                activeManualSegment;


            skippedSegments.add(
                getSegmentKey(
                    segment
                )
            );


            activeManualSegment =
                null;


            hideManualSkipButton();


            /*
             * Show the notification before
             * seeking so it is already visible
             * when the video jumps.
             */

            showSkippedPopup();


            skipSponsor(
                segment.end
            );
        }
    );


    attachManualButton();
}


/*
 * =========================================================
 * ATTACH MANUAL BUTTON
 * =========================================================
 */

function attachManualButton() {

    if (
        !manualSkipButton
    ) {
        return;
    }


    const player =
        document.querySelector(
            "#movie_player"
        );


    if (
        !player
    ) {
        return;
    }


    if (
        manualSkipButton.parentElement ===
        player
    ) {
        return;
    }


    /*
     * Make the player the positioning
     * container for the button.
     */

    if (
        getComputedStyle(player).position ===
        "static"
    ) {

        player.style.position =
            "relative";
    }


    try {

        player.appendChild(
            manualSkipButton
        );

    } catch (error) {

        console.log(
            "SponsorSkip: could not attach manual button."
        );
    }
}


/*
 * =========================================================
 * HIDE MANUAL BUTTON
 * =========================================================
 */

function hideManualSkipButton() {

    if (
        !manualSkipButton
    ) {
        return;
    }


    manualSkipButton.style.display =
        "none";


    activeManualSegment =
        null;
}


/*
 * =========================================================
 * SHOW MANUAL BUTTON
 * =========================================================
 */

function showManualSkipButton(
    segment
) {

    if (
        autoSkip
    ) {
        return;
    }


    if (
        !manualSkipButton
    ) {
        createManualSkipButton();
    }


    attachManualButton();


    activeManualSegment =
        segment;


    manualSkipButton.style.display =
        "flex";
}


/*
 * =========================================================
 * UPDATE MANUAL BUTTON
 * =========================================================
 */

function updateManualSkipButton() {

    if (
        autoSkip
    ) {

        hideManualSkipButton();

        return;
    }


    if (
        !activeManualSegment
    ) {

        hideManualSkipButton();
    }
}


/*
 * =========================================================
 * SEGMENT KEY
 * =========================================================
 */

function getSegmentKey(
    segment
) {

    return (
        `${segment.start}-${segment.end}`
    );
}


/*
 * =========================================================
 * SKIP SPONSOR
 * =========================================================
 *
 * Direct seek.
 *
 * No fade.
 * No blur.
 *
 * This preserves the seamless behavior that
 * was tested successfully.
 */

function skipSponsor(
    time
) {

    if (
        !videoElement
    ) {
        return;
    }


    console.log(
        `SponsorSkip: jumping to ${time.toFixed(2)}s`
    );


    try {

        videoElement.currentTime =
            time;

    } catch (error) {

        console.log(
            "SponsorSkip: could not seek video."
        );
    }
}


/*
 * =========================================================
 * CHECK SPONSOR POSITION
 * =========================================================
 */

function checkSponsorPosition() {

    if (
        !videoElement
    ) {
        return;
    }


    if (
        !sponsorSegments.length
    ) {
        return;
    }


    /*
     * If sponsor detection is still running, don't
     * attempt to skip anything yet.
     */

    if (
        detectionInProgress
    ) {
        return;
    }


    if (
        videoElement.paused
    ) {
        return;
    }


    const currentTime =
        videoElement.currentTime;


    for (
        const segment of sponsorSegments
    ) {

        const key =
            getSegmentKey(
                segment
            );


        if (
            skippedSegments.has(
                key
            )
        ) {
            continue;
        }


        /*
         * Start the skip 1.5 seconds before
         * the sponsor starts.
         */

        const triggerTime =
            Math.max(
                0,
                segment.start -
                    PRE_SKIP_SECONDS
            );


        if (
            currentTime >= triggerTime &&
            currentTime < segment.end
        ) {

            /*
             * =================================================
             * AUTO MODE
             * =================================================
             */

            if (
                autoSkip
            ) {

                skippedSegments.add(
                    key
                );


                isSkipping =
                    true;


                /*
                 * Show the popup BEFORE seeking.
                 */

                showSkippedPopup();


                /*
                 * Jump directly to the end of
                 * the detected sponsor segment.
                 */

                skipSponsor(
                    segment.end
                );


                requestAnimationFrame(
                    () => {

                        isSkipping =
                            false;
                    }
                );


                return;
            }


            /*
             * =================================================
             * MANUAL MODE
             * =================================================
             */

            showManualSkipButton(
                segment
            );


            return;
        }
    }


    /*
     * Hide the manual button if playback has moved
     * away from the sponsor trigger window.
     */

    if (
        !autoSkip &&
        activeManualSegment
    ) {

        const segment =
            activeManualSegment;


        const triggerTime =
            Math.max(
                0,
                segment.start -
                    PRE_SKIP_SECONDS
            );


        if (
            currentTime <
            triggerTime
        ) {

            hideManualSkipButton();
        }
    }
}


/*
 * =========================================================
 * PLAYBACK CHECKER
 * =========================================================
 */

function startPlaybackChecker() {

    if (
        playbackCheckInterval !== null
    ) {
        return;
    }


    playbackCheckInterval =
        setInterval(
            () => {

                if (
                    extensionContextInvalidated
                ) {

                    clearInterval(
                        playbackCheckInterval
                    );

                    playbackCheckInterval =
                        null;

                    return;
                }


                if (
                    !videoElement
                ) {
                    return;
                }


                if (
                    videoElement.paused ||
                    videoElement.ended
                ) {
                    return;
                }


                if (
                    isSkipping ||
                    detectionInProgress
                ) {
                    return;
                }


                checkSponsorPosition();

            },
            100
        );
}


/*
 * =========================================================
 * STOP PLAYBACK CHECKER
 * =========================================================
 */

function stopPlaybackChecker() {

    if (
        playbackCheckInterval !== null
    ) {

        clearInterval(
            playbackCheckInterval
        );

        playbackCheckInterval =
            null;
    }
}


/*
 * =========================================================
 * ATTACH TO VIDEO
 * =========================================================
 */

function attachToVideo() {

    const video =
        document.querySelector(
            "video"
        );


    if (
        !video
    ) {
        return;
    }


    /*
     * If this is already our active video,
     * make sure the UI is still attached.
     */

    if (
        videoElement ===
        video
    ) {

        attachManualButton();

        startPlaybackChecker();


        /*
         * If sponsor detection is still running,
         * make sure the play protection is attached.
         */

        if (
            detectionInProgress
        ) {

            attachDetectionPlayHandler(
                video
            );
        }


        return;
    }


    /*
     * Remove listener from old video.
     */

    if (
        videoElement &&
        timeUpdateHandler
    ) {

        try {

            videoElement.removeEventListener(
                "timeupdate",
                timeUpdateHandler
            );

        } catch (error) {

            /*
             * Old video element may already be gone.
             */
        }
    }


    /*
     * Remove detection play handler from old video.
     */

    if (
        videoElement &&
        detectionPlayHandler
    ) {

        try {

            videoElement.removeEventListener(
                "play",
                detectionPlayHandler
            );

        } catch (error) {

            /*
             * Ignore old video errors.
             */
        }
    }


    videoElement =
        video;


    /*
     * Create the timeupdate handler.
     */

    timeUpdateHandler =
        () => {

            if (
                isSkipping
            ) {
                return;
            }


            checkSponsorPosition();
        };


    videoElement.addEventListener(
        "timeupdate",
        timeUpdateHandler
    );


    /*
     * If detection is currently running for this video,
     * protect playback immediately.
     */

    if (
        detectionInProgress &&
        detectionVideoId ===
        currentVideoId
    ) {

        attachDetectionPlayHandler(
            videoElement
        );


        /*
         * If the video was already playing when the new
         * video element appeared, pause it and remember
         * that we should resume afterwards.
         */

        if (
            !videoElement.paused &&
            !videoElement.ended
        ) {

            resumeAfterDetection =
                true;


            videoElement.pause();
        }
    }


    /*
     * Create and attach manual button.
     */

    createManualSkipButton();

    attachManualButton();


    /*
     * Start the more precise 100ms checker.
     */

    startPlaybackChecker();


    console.log(
        "SponsorSkip: attached to YouTube video."
    );
}


/*
 * =========================================================
 * CANCEL BACKGROUND REQUEST
 * =========================================================
 */

function cancelBackgroundRequest() {

    /*
     * Sponsor requests are now made directly from the
     * content script to FastAPI.
     */

    return;
}


/*
 * =========================================================
 * HANDLE VIDEO CHANGE
 * =========================================================
 */

function handleVideoChange() {

    /*
     * If the extension context has disappeared,
     * there is nothing more this old content script
     * should do.
     */

    if (
        !isExtensionContextValid()
    ) {
        return;
    }


    const videoId =
        getVideoId();


    /*
     * =====================================================
     * NO ACTIVE VIDEO
     * =====================================================
     */

    if (
        !videoId
    ) {

        console.log(
            "SponsorSkip: no active video."
        );


        navigationGeneration += 1;


        requestVideoId =
            null;


        cancelBackgroundRequest();


        currentVideoId =
            null;


        sponsorSegments =
            [];


        skippedSegments.clear();


        activeManualSegment =
            null;


        isSkipping =
            false;


        detectionInProgress =
            false;

        detectionVideoId =
            null;

        resumeAfterDetection =
            false;


        hideDetectionOverlay();


        hideManualSkipButton();


        stopPlaybackChecker();


        return;
    }


    /*
     * =====================================================
     * SAME VIDEO
     * =====================================================
     */

    if (
        videoId ===
        currentVideoId
    ) {

        attachToVideo();

        return;
    }


    /*
     * =====================================================
     * NEW VIDEO
     * =====================================================
     */

    console.log(
        "SponsorSkip: video changed."
    );


    console.log(
        "SponsorSkip: previous video:",
        currentVideoId
    );


    console.log(
        "SponsorSkip: new video:",
        videoId
    );


    /*
     * Only a real video change creates a new generation.
     * This invalidates all old asynchronous responses.
     */

    navigationGeneration += 1;

    const generation =
        navigationGeneration;


    /*
     * Invalidate the previous request BEFORE
     * starting the new request.
     */

    requestVideoId =
        null;


    cancelBackgroundRequest();


    /*
     * Stop checking the previous video.
     */

    stopPlaybackChecker();


    /*
     * Clear old sponsor segments immediately.
     */

    sponsorSegments =
        [];


    skippedSegments.clear();


    activeManualSegment =
        null;


    isSkipping =
        false;


    /*
     * =====================================================
     * START FIRST-PLAY DETECTION GATE
     * =====================================================
     *
     * This happens BEFORE the backend request.
     *
     * Therefore a newly loaded video cannot outrun
     * sponsor detection.
     */

    detectionInProgress =
        false;

    detectionVideoId =
        null;

    resumeAfterDetection =
        false;


    hideManualSkipButton();


    /*
     * Remove an old popup if one exists.
     */

    if (
        popupElement
    ) {

        popupElement.remove();

        popupElement =
            null;
    }


    if (
        popupTimeout
    ) {

        clearTimeout(
            popupTimeout
        );

        popupTimeout =
            null;
    }


    /*
     * Remove any old detection overlay.
     */

    hideDetectionOverlay();


    /*
     * Set the new video immediately.
     */

    currentVideoId =
        videoId;


    /*
     * Attach to the new video element.
     *
     * If it is already playing, the detection gate
     * will pause it.
     */

    attachToVideo();


    /*
     * Start the real sponsor detection request.
     *
     * The generation value protects us if another
     * navigation happens before the backend responds.
     */

    fetchSponsorSegments(
        videoId,
        generation
    );
}


/*
 * =========================================================
 * YOUTUBE SPA NAVIGATION
 * =========================================================
 */

document.addEventListener(
    "yt-navigate-finish",
    () => {

        if (
            extensionContextInvalidated
        ) {
            return;
        }


        console.log(
            "SponsorSkip: YouTube navigation finished."
        );


        handleVideoChange();


        /*
         * YouTube may create the video element slightly
         * after the navigation event.
         */

        setTimeout(
            () => {

                if (
                    extensionContextInvalidated
                ) {
                    return;
                }


                attachToVideo();

            },
            500
        );
    }
);


/*
 * =========================================================
 * URL CHANGE MONITOR
 * =========================================================
 */

let lastKnownUrl =
    window.location.href;


const urlMonitor =
    setInterval(
        () => {

            /*
             * Stop doing work if this extension context
             * has been invalidated.
             */

            if (
                extensionContextInvalidated
            ) {

                clearInterval(
                    urlMonitor
                );

                stopPlaybackChecker();

                return;
            }


            const currentUrl =
                window.location.href;


            if (
                currentUrl !==
                lastKnownUrl
            ) {

                console.log(
                    "SponsorSkip: URL changed."
                );


                lastKnownUrl =
                    currentUrl;


                handleVideoChange();
            }

        },
        500
    );


/*
 * =========================================================
 * MODE CHANGE FROM POPUP
 * =========================================================
 */

if (
    isExtensionContextValid()
) {

    try {

        chrome.runtime.onMessage.addListener(
            (message) => {

                if (
                    extensionContextInvalidated
                ) {
                    return;
                }


                if (
                    !message ||
                    message.type !==
                    "MODE_CHANGED"
                ) {
                    return;
                }


                console.log(
                    "SponsorSkip: mode changed to:",
                    message.autoSkip
                        ? "Auto Skip"
                        : "Manual Skip"
                );


                autoSkip =
                    Boolean(
                        message.autoSkip
                    );


                /*
                 * Remove the manual button whenever
                 * the mode changes.
                 */

                hideManualSkipButton();


                /*
                 * The button will appear again automatically
                 * if Manual mode is active and a sponsor is
                 * approaching.
                 */

                updateManualSkipButton();
            }
        );

    } catch (error) {

        if (
            error &&
            typeof error.message ===
            "string" &&
            error.message.includes(
                "Extension context invalidated"
            )
        ) {

            extensionContextInvalidated =
                true;
        }
    }
}


/*
 * =========================================================
 * MUTATION OBSERVER
 * =========================================================
 */

const observer =
    new MutationObserver(
        () => {

            if (
                extensionContextInvalidated
            ) {

                observer.disconnect();

                return;
            }


            attachToVideo();

            attachManualButton();
        }
    );


observer.observe(
    document.body,
    {
        childList: true,
        subtree: true
    }
);


/*
 * =========================================================
 * INITIALIZATION
 * =========================================================
 */

loadSettings();

handleVideoChange();