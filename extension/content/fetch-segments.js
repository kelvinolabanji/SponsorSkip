/*
 This request goes directly from the content script to the local FastAPI server
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
            }
        );
}


