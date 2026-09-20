/*
PLAYBACK CHECKER
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
                    isSkipping
                ) {
                    return;
                }


                checkSponsorPosition();

            },
            100
        );
}


/*
 stop PLAYBACK CHECKER
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


