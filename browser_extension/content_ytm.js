// content_ytm.js

function getInfo() {
    try {
        const title = document.querySelector(".title.style-scope.ytmusic-player-bar")?.textContent?.trim();
        const byline = document.querySelector(".byline.style-scope.ytmusic-player-bar")?.textContent?.trim();
        const img = document.querySelector(".image.style-scope.ytmusic-player-bar")?.src;

        // Progress
        const progress = document.querySelector("#progress-bar");
        const currentTime = progress?.getAttribute("aria-valuenow");
        const totalTime = progress?.getAttribute("aria-valuemax");

        // Status
        const playButton = document.querySelector("#play-pause-button");
        const isPlaying = playButton?.getAttribute("title") === "Pause"; // If title is Pause, it means it's playing

        if (!title) return null;

        // Parse Artist/Album from byline (Format: "Artist • Album • Year")
        let artist = byline;
        let album = "";

        if (byline && byline.includes("•")) {
            const parts = byline.split("•");
            artist = parts[0].trim();
            if (parts.length > 1) album = parts[1].trim();
        }

        return {
            source: "youtube_music",
            title: title,
            artist: artist,
            album: album,
            cover: img,
            url: window.location.href, // [NUEVO] URL para el botón
            current_time: parseFloat(currentTime || 0),
            total_time: parseFloat(totalTime || 0),
            is_playing: isPlaying
        };
    } catch (e) {
        return null;
    }
}

// Loop to send data
const intervalId = setInterval(() => {
    const data = getInfo();
    if (data) {
        try {
            chrome.runtime.sendMessage(data);
        } catch (e) {
            // Extension context invalidated (Extension reloaded or disabled)
            console.log("MediaRPC: Connection lost. Stopping script.");
            clearInterval(intervalId);
        }
    }
}, 1000);
