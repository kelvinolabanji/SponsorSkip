const toggle =
    document.getElementById(
        "autoSkipToggle"
    );

const modeTitle =
    document.getElementById(
        "modeTitle"
    );

const modeDescription =
    document.getElementById(
        "modeDescription"
    );


/*
 * Load the saved skipping mode.
 *
 * Auto Skip is enabled by default.
 */
chrome.storage.sync.get(
    {
        autoSkip: true
    },
    (settings) => {

        toggle.checked =
            settings.autoSkip;

        updateUI(
            settings.autoSkip
        );
    }
);


/*
 * Update the popup based on
 * the selected mode.
 */
function updateUI(autoSkip) {

    if (autoSkip) {

        modeTitle.textContent =
            "Auto Skip";

        modeDescription.textContent =
            "SponsorSkip automatically skips detected sponsored segments.";

    } else {

        modeTitle.textContent =
            "Manual Skip";

        modeDescription.textContent =
            "SponsorSkip shows a Skip Sponsor button when an ad is detected.";
    }
}


/*
 * Save mode whenever the toggle
 * is changed.
 */
toggle.addEventListener(
    "change",
    () => {

        const autoSkip =
            toggle.checked;

        chrome.storage.sync.set(
            {
                autoSkip
            }
        );

        updateUI(
            autoSkip
        );


        /*
         * Tell the active YouTube tab
         * about the mode change.
         */
        chrome.tabs.query(
            {
                active: true,
                currentWindow: true
            },
            (tabs) => {

                if (!tabs.length) {
                    return;
                }

                const tab =
                    tabs[0];

                if (
                    !tab.url ||
                    !tab.url.includes(
                        "youtube.com"
                    )
                ) {
                    return;
                }

                chrome.tabs.sendMessage(
                    tab.id,
                    {
                        type: "MODE_CHANGED",
                        autoSkip
                    }
                );
            }
        );
    }
);