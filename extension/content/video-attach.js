/*
attach to video
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


