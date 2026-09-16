console.log("SponsorSkip loaded");

function getVideoId() {
    const url = new URL(window.location.href);
    return url.searchParams.get("v");
}

function getSponsorSegments() {
    const videoId = getVideoId();

    console.log("YouTube Video ID:", videoId);
    console.log("Requesting sponsor segments...");

    chrome.runtime.sendMessage(
        {
            type: "GET_SEGMENTS",
            videoId: videoId
        },
        (response) => {
            if (chrome.runtime.lastError) {
                console.error(
                    "SponsorSkip message error:",
                    chrome.runtime.lastError.message
                );
                return;
            }

            console.log("Response from background:", response);

            if (response.success) {
                console.log("Sponsor segments:", response.data.segments);
            } else {
                console.error("Failed to get segments:", response.error);
            }
        }
    );
}

getSponsorSegments();