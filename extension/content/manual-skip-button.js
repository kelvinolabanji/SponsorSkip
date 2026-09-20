/*
 CREATE MANUAL SKIP BUTTON
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
 
ATTACH MANUAL BUTTON

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
  HIDE MANUAL BUTTON */

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
show MANUAL BUTTON
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
UPDATE MANUAL BUTTON
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


