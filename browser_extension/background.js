// background.js

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message) {
        fetch("http://127.0.0.1:9696/update", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(message)
        }).catch(err => {
            // Ignore connection errors (app might be closed)
        });
    }
});
