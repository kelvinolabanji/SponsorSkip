/* SAFE EXTENSION CONTEXT CHECK*/

function isExtensionContextValid() {

    if (
        extensionContextInvalidated
    ) {
        return false;
    }

    try {

        const id =
            chrome.runtime.id;

        return Boolean(id);

    } catch (error) {

        extensionContextInvalidated =
            true;

        return false;
    }
}
