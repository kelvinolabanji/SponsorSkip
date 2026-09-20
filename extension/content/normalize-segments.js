/*
 * NORMALIZE SEGMENTS
 */

function normalizeSegments(
    segments
) {

    if (
        !Array.isArray(
            segments
        )
    ) {
        return [];
    }


    return segments

        .map(
            segment => {

                return {

                    start:
                        Number(
                            segment.start
                        ),

                    end:
                        Number(
                            segment.end
                        )
                };
            }
        )

        .filter(
            segment => {

                return (

                    Number.isFinite(
                        segment.start
                    ) &&

                    Number.isFinite(
                        segment.end
                    ) &&

                    segment.end >
                    segment.start
                );
            }
        )

        .sort(
            (a, b) =>
                a.start - b.start
        );
}


