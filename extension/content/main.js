/* YOUTUBE SPA NAVIGATION*/

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


/*URL CHANGE MONITOR*/

let lastKnownUrl =
    window.location.href;


const urlMonitor =
    setInterval(
        () => {

            /*
             * Stops doing work if this extension context
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


/*MODE CHANGE FROM POPUP*/
 

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
  MUTATION OBSERVER
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

 INITIALIZATION
 
 */

loadSettings();

handleVideoChange();