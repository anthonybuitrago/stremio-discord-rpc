# 🚀 MediaRPC v5.6.3

**MediaRPC** is an advanced Discord Rich Presence (RPC) tool optimized for **HiAnime** and **YouTube Music** on Windows. It seamlessly integrates a **Browser Extension** with a lightweight desktop client to display your media activity in real-time.

## ✨ New in v5.6.3

### 📺 HiAnime Integration (Advanced)
- **Exact Season Posters**: Scrapes the specific cover art for the season you are watching (e.g., *My Hero Academia Season 7*), instead of generic series posters.
- **Smart Movie Display**: Automatically detects movies and hides "Episode 1" for a cleaner, title-only look.
- **Anti-Flicker Technology**: Intelligent deduplication prevents your Discord status from flashing or resetting unnecessarily.
- **Robust Episode Detection**: Uses multiple DOM selectors to guarantee episode numbers are captured correctly.

### 🎵 YouTube Music (Enhanced)
- **Silent Pause**: Pausing music instantly clears your Discord activity without spamming your local logs.
- **Instant Resume**: Resuming playback triggers an immediate status update, even for the same song.
- **Smart Switching**: Seamlessly transitions between Local Desktop detection and Browser Extension detection without log spam.

### 🛠️ Core Improvements
- **Clean Logs**: Console output is now 100% English, emoji-coded, and free of technical noise.
- **Low Profile**: Runs silently in the system tray with minimal resource usage.

---

## 📥 Installation

1. **Download**: Get the latest `MediaRPC.exe` from the Releases page.
2. **Install Extension**:
   - Go to `chrome://extensions` in your browser (Chrome/Edge/Brave).
   - Enable **Developer Mode** (top right switch).
   - Click **"Load unpacked"** and select the `browser_extension` folder included in the release.
3. **Run**: Double-click `MediaRPC.exe`. You will see a satellite icon (🛰️) in your system tray.

---

## 🎮 Usage

- **Just Watch**: Open **HiAnime.to** and start any video. Discord will update automatically.
- **Just Listen**: Open **music.youtube.com**. Discord will show your song with high-res album art.

> **Note**: If you restart your browser, simply reload the tab to reconnect to MediaRPC.

---

## ⚙️ Configuration

A `config.json` is created automatically. Access it via Tray Menu -> **Configuración**.

```json
{
    "client_id": "YOUR_DISCORD_APP_ID",
    "music_client_id": "OPTIONAL_MUSIC_APP_ID",
    "show_search_button": true,
    "enable_music_rpc": true
}
```

## 📜 License
MIT License.