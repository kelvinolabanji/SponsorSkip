function handleVideoChange() {

    /*
    If the extension context has disappeared,there is nothing more this old content script should do.
     */

    if (
        !isExtensionContextValid()
    ) {
        return;
    }


    const videoId =
        getVideoId();



    if (
        !videoId
    ) {

        console.log(
            "SponsorSkip: no active video."
        );


        navigationGeneration += 1;


        requestVideoId =
            null;


        currentVideoId =
            null;


        sponsorSegments =
            [];


        skippedSegments.clear();


        activeManualSegment =
            null;


        isSkipping =
            false;


        hideManualSkipButton();


        stopPlaybackChecker();


        return;
    }


  

    if (
        videoId ===
        currentVideoId
    ) {

        attachToVideo();

        return;
    }


 
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


   

    currentVideoId =
        videoId;


    
    attachToVideo();



    fetchSponsorSegments(
        videoId,
        generation
    );
}


