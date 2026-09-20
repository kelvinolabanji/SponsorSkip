/*
 * SponsorSkip background service worker
 *
 * Handles communication between the content script
 * and the SponsorSkip FastAPI backend.
 *
 * Requests are tracked per YouTube tab so that when
 * the user changes videos, the previous request can
 * be cancelled safely.
 */


const activeRequests = new Map();


/*
 * =========================================================
 * MESSAGE HANDLER
 * =========================================================
 */

chrome.runtime.onMessage.addListener(
    (message, sender, sendResponse) => {

        /*
         * =====================================================
         * GET SPONSOR SEGMENTS
         * =====================================================
         */

        if (message.type === "GET_SEGMENTS") {

            const videoId =
                message.videoId;

            const tabId =
                sender.tab
                    ? sender.tab.id
                    : null;


            if (!videoId) {

                sendResponse({
                    success: false,
                    error: "No video ID provided."
                });

                return false;
            }


            /*
             * Cancel any existing request for this tab.
             */

            if (
                tabId !== null &&
                activeRequests.has(tabId)
            ) {

                const previousRequest =
                    activeRequests.get(tabId);


                console.log(
                    "Background: cancelling previous request for:",
                    previousRequest.videoId
                );


                previousRequest.controller.abort();


                activeRequests.delete(
                    tabId
                );
            }


            /*
             * Create a controller for this request.
             */

            const controller =
                new AbortController();


            /*
             * Store request information.
             */

            if (tabId !== null) {

                activeRequests.set(
                    tabId,
                    {
                        controller: controller,
                        videoId: videoId
                    }
                );
            }


            console.log(
                "Background: requesting segments for:",
                videoId
            );


            /*
             * =================================================
             * BACKEND REQUEST
             * =================================================
             */

            fetch(
                `http://localhost:8001/segments/${videoId}`,
                {
                    signal: controller.signal
                }
            )

                /*
                 * ---------------------------------------------
                 * HTTP RESPONSE
                 * ---------------------------------------------
                 */

                .then(response => {

                    console.log(
                        "Background: HTTP status:",
                        response.status,
                        "for:",
                        videoId
                    );


                    if (!response.ok) {

                        throw new Error(
                            `HTTP ${response.status}`
                        );
                    }


                    return response.json();
                })


                /*
                 * ---------------------------------------------
                 * RESPONSE DATA
                 * ---------------------------------------------
                 */

                .then(data => {

                    /*
                     * Check whether this request is still
                     * the active request for this tab.
                     */

                    if (
                        tabId !== null
                    ) {

                        const activeRequest =
                            activeRequests.get(
                                tabId
                            );


                        if (
                            !activeRequest ||
                            activeRequest.controller !==
                                controller ||
                            activeRequest.videoId !==
                                videoId
                        ) {

                            console.log(
                                "Background: ignoring stale response for:",
                                videoId
                            );

                            return;
                        }
                    }


                    console.log(
                        "Background: received segments for:",
                        videoId
                    );


                    sendResponse({
                        success: true,
                        data: data
                    });
                })


                /*
                 * ---------------------------------------------
                 * ERROR HANDLING
                 * ---------------------------------------------
                 */

                .catch(error => {

                    /*
                     * Request cancellation is expected when
                     * the user changes videos.
                     */

                    if (
                        error.name ===
                        "AbortError"
                    ) {

                        console.log(
                            "Background: request cancelled for:",
                            videoId
                        );


                        /*
                         * Respond to the content script so
                         * Chrome does not report an unhandled
                         * message-channel error.
                         */

                        sendResponse({
                            success: false,
                            cancelled: true,
                            error: "Request cancelled."
                        });


                        return;
                    }


                    /*
                     * Real backend error.
                     */

                    console.error(
                        "Background: API error for:",
                        videoId,
                        error
                    );


                    /*
                     * Only report the error if this request
                     * is still the active request.
                     */

                    if (
                        tabId !== null
                    ) {

                        const activeRequest =
                            activeRequests.get(
                                tabId
                            );


                        if (
                            !activeRequest ||
                            activeRequest.controller !==
                                controller
                        ) {

                            return;
                        }
                    }


                    sendResponse({
                        success: false,
                        cancelled: false,
                        error: error.message
                    });
                })


                /*
                 * ---------------------------------------------
                 * CLEANUP
                 * ---------------------------------------------
                 */

                .finally(() => {

                    if (
                        tabId !== null
                    ) {

                        const activeRequest =
                            activeRequests.get(
                                tabId
                            );


                        /*
                         * Only delete this request if it is
                         * still the active request.
                         */

                        if (
                            activeRequest &&
                            activeRequest.controller ===
                                controller
                        ) {

                            activeRequests.delete(
                                tabId
                            );
                        }
                    }
                });


            /*
             * Keep the message channel open while the
             * backend request is running.
             */

            return true;
        }


        /*
         * =====================================================
         * CANCEL REQUEST
         * =====================================================
         */

        if (
            message.type ===
            "CANCEL_REQUEST"
        ) {

            const tabId =
                sender.tab
                    ? sender.tab.id
                    : null;


            if (
                tabId !== null &&
                activeRequests.has(tabId)
            ) {

                const activeRequest =
                    activeRequests.get(
                        tabId
                    );


                console.log(
                    "Background: cancelling request for:",
                    activeRequest.videoId
                );


                activeRequest.controller.abort();


                activeRequests.delete(
                    tabId
                );
            }


            return false;
        }
    }
);


/*
 * =========================================================
 * TAB CLOSED
 * =========================================================
 */

chrome.tabs.onRemoved.addListener(
    (tabId) => {

        if (
            activeRequests.has(tabId)
        ) {

            const activeRequest =
                activeRequests.get(
                    tabId
                );


            console.log(
                "Background: tab closed, cancelling request for:",
                activeRequest.videoId
            );


            activeRequest.controller.abort();


            activeRequests.delete(
                tabId
            );
        }
    }
);