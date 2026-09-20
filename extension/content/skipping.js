/*
segment key
 */

function getSegmentKey(
    segment
) {

    return (
        `${segment.start}-${segment.end}`
    );
}


/*
 skip sponsor
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
check sponsor position
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
             manual mode
             */

            showManualSkipButton(
                segment
            );


            return;
        }
    }


    /*
     Hide the manual button if playback has moved
     away from the sponsor trigger window.
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


