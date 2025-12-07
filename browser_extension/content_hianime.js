// content_hianime.js

function getInfo() {
    try {
        // [STRICT] Only process if we are on a watch page
        if (!window.location.href.includes("/watch/")) {
            return null;
        }

        const data = {
            source: "hianime",
            url: window.location.href,
            timestamp: Date.now()
        };

        // --- 1. PLAYBACK & VISIBILITY DATA ---
        const video = document.querySelector("video");

        // [NUEVO] Si la pestaña está oculta (minimizada o en otro tab), forzamos pausa
        const isHidden = document.hidden;
        data.is_hidden = isHidden; // GLOBAL: Sent even if no video found

        if (video) {
            data.type = "playback";
            // Está sonando SOLO si el video corre Y la pestaña es visible
            data.is_playing = !video.paused && !isHidden;
            data.current_time = video.currentTime;
            data.total_time = video.duration;
        }

        // --- 2. METADATA (Main Page) ---
        // Try to find title in standard locations
        const titleEl = document.querySelector(".film-name a") ||
            document.querySelector(".anisc-detail .film-name") ||
            document.querySelector("h2.film-name") ||
            document.querySelector(".film-name") ||
            document.querySelector("#anime-name");

        if (titleEl) {
            data.title = titleEl.textContent.trim();
        }

        // --- 2.1 POSTER (Scrape from page) ---
        // Try to find the poster image to show the specific season cover
        const posterEl = document.querySelector(".film-poster .film-poster-img") ||
            document.querySelector(".anisc-poster .film-poster-img") ||
            document.querySelector("img.film-poster-img");

        if (posterEl && posterEl.src) {
            data.poster = posterEl.src;
        }

        // --- 3. FALLBACKS ---
        if (!data.title && (window.location.host.includes("hianime") || !video)) {
            const pageTitle = document.title;
            // Common format: "Watch One Piece Episode 1 English Sub ..."
            if (pageTitle.includes("Watch")) {
                const parts = pageTitle.replace("Watch", "").split("Episode");
                if (parts.length > 0) data.title = parts[0].trim();
            } else {
                data.title = pageTitle.split("|")[0].trim();
            }
        }

        // Determine Type if not set
        if (!data.type) {
            if (data.title) data.type = "meta";
            else if (video) data.type = "playback";
        }

        // Episode Parsing
        if (data.type === "meta" || data.type === "mixed") {
            // Try MULTIPLE selectors for the active episode button
            // HiAnime changes these often. We look for 'active' and 'ep-item'/'ssl-item-ep'
            const activeEp = document.querySelector(".ssl-item-ep.active .ep-name") ||
                document.querySelector(".ssl-item-ep.active") ||
                document.querySelector(".ep-item.active") ||
                document.querySelector(".btn-ep.active") ||
                document.querySelector(".ss-list a.active") ||
                document.querySelector("a.active[data-number]");

            if (activeEp) {
                // Try to get data-number first (most accurate)
                if (activeEp.dataset && activeEp.dataset.number) {
                    data.episode = `Episode ${activeEp.dataset.number}`;
                } else {
                    data.episode = activeEp.textContent.trim();
                }

                // Ensure format "Episode X"
                if (!data.episode.toLowerCase().includes("episode")) {
                    data.episode = `Episode ${data.episode}`;
                }
            } else {
                // Fallback: Parse from Document Title (Most reliable for Basic Mode)
                // Format: "Watch One Piece Episode 3 English Sub..."
                const titleMatch = document.title.match(/Episode\s+(\d+)/i);
                if (titleMatch) {
                    data.episode = `Episode ${titleMatch[1]}`;
                }
                // Fallback 2: Check URL for slug "episode-3" (NOT ?ep=ID)
                else {
                    const slugMatch = window.location.pathname.match(/episode-(\d+)/);
                    if (slugMatch) {
                        data.episode = `Episode ${slugMatch[1]}`;
                    }
                }
            }
        }

        // IMPORTANT: Only return NULL if we really have NOTHING
        if (!data.type && !data.title) {
            return null;
        }

        return data;

    } catch (e) {
        console.error("MediaRPC Error:", e);
        return null;
    }
}

// Send data every 1 second
setInterval(() => {
    let data = getInfo();

    // [DEBUG] Always send a heartbeat if no data found
    if (!data) {
        // Only send ping if we are on a watch page (to verify connection)
        if (window.location.href.includes("/watch/")) {
            data = {
                source: "hianime",
                type: "ping",
                url: window.location.href,
                title: "Verifying Connection..."
            };
        }
    }

    if (data) {
        try {
            chrome.runtime.sendMessage(data);
        } catch (e) {
            // Extension context invalidated
        }
    }
}, 1000);
