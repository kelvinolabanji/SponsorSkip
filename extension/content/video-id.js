function getVideoId() {

    try {

        const url =
            new URL(
                window.location.href
            );

       

        return url.searchParams.get(
            "v"
        );

    } catch (error) {

        console.log(
            "SponsorSkip: failed to read video ID.",
            error
        );

        return null;
    }
}


