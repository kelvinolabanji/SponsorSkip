chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "GET_SEGMENTS") {
        console.log("Background: requesting segments for:", message.videoId);

        fetch(`http://localhost:8001/segments/${message.videoId}`)
            .then(response => {
                console.log("Background: HTTP status:", response.status);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                return response.json();
            })
            .then(data => {
                console.log("Background: API response:", data);

                sendResponse({
                    success: true,
                    data: data
                });
            })
            .catch(error => {
                console.error("Background: API error:", error);

                sendResponse({
                    success: false,
                    error: error.message
                });
            });

        return true;
    }
});