/*
show SKIPPED POPUP
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


