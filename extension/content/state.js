/*
 Handles:
    - state management
 */

console.log(
    "SponsorSkip content script loaded"
);


let currentVideoId = null;
let requestVideoId = null;
let sponsorSegments = [];
let skippedSegments = new Set();

let videoElement = null;
let timeUpdateHandler = null;

let popupElement = null;
let popupTimeout = null;

let isSkipping = false;
let autoSkip = true;

let manualSkipButton = null;
let activeManualSegment = null;

let playbackCheckInterval = null;


/*
 Used to invalidate old navigation/request cycles. Every time the user navigates to another YouTube page,this number increases. Old callbacks can then safely detect that they belong to an outdated navigation cycle.
 */

let navigationGeneration = 0;


/*
 Prevents the old content script from continuing to do unnecessary work after the extension context disappears.
 */

let extensionContextInvalidated = false;



const PRE_SKIP_SECONDS = 1.5;


