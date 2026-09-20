/*
load SETTINGS
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


