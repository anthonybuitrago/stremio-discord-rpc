// content_stremio.js

function getInfo() {
    try {
        // Stremio Web DOM is dynamic. We look for the player UI.
        // Note: Selectors might need adjustment based on Stremio Web version.

        // This is a guess based on common Stremio Web structure.
        // Usually there's a title container in the player overlay.

        const titleEl = document.querySelector(".player-title"); // Hypothetical
        if (!titleEl) return null;

        const title = titleEl.textContent.trim();

        // Check if playing
        const video = document.querySelector("video");
        const isPlaying = video && !video.paused;

        return {
            source: "stremio_web",
            title: title,
            is_playing: isPlaying,
            current_time: video ? video.currentTime : 0,
            total_time: video ? video.duration : 0
        };
    } catch (e) {
        return null;
    }
}

setInterval(() => {
    const data = getInfo();
    if (data) {
        chrome.runtime.sendMessage(data);
    }
}, 1000);
