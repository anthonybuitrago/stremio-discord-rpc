# General Description

**Stremio Discord RPC** is a software engineering project developed by **Anthony Buitrago**. It serves as a lightweight, standalone integration tool designed to bridge the gap between the Stremio media player and the Discord Rich Presence system. Currently, Stremio lacks native integration with Discord on Windows, leaving users without the ability to display their activity automatically.

This project solves that problem by creating a background process that monitors local playback activity and updates the user's Discord profile in real-time. It features a robust "Anti-Buffer" system, intelligent metadata retrieval with caching, and a non-intrusive system tray interface.

## Key Features
- **Real-time Status**: Updates Discord with the movie/series you are watching.
- **Smart Metadata**: Fetches high-quality cover art from Cinemeta.
- **Robustness**: Auto-reconnects if Stremio is closed or network fails.
- **Performance**: In-memory caching to reduce API calls.
- **Logging**: Rotating log system to keep disk usage low.

# Description of the System Architecture and API Interaction

The system operates on a **multi-threaded architecture**, separating the graphical user interface (System Tray) from the logical processing loop to ensure stability and responsiveness.

**1. Local Data Acquisition (Stremio API):**
The application connects to Stremio's local server endpoint (`http://127.0.0.1:11470/stats.json`). It retrieves raw playback data, including the filename and streaming status. This local API is polled at configurable intervals to detect changes in activity.

**2. Data Processing and Cleaning (Regex Engine):**
Raw filenames from torrents or streams often contain technical "noise" (e.g., `[1080p]`, `x265`, `AAC`). The system utilizes the `re` library (Regular Expressions) to sanitize strings based on a customizable blacklist defined in `config.json`.

**3. Metadata Enrichment (Cinemeta API):**
Once the title is sanitized, the system performs a GET request to the **Cinemeta API** (Stremio's official catalog). It queries the specific movie or series to retrieve the official poster URL (Cover Art). This ensures that the Discord status displays high-quality artwork instead of a generic logo.

**4. Discord Rich Presence (IPC):**
Finally, the processed data (Clean Title, Poster URL, Elapsed Time) is sent to the local Discord client using the `pypresence` library via Inter-Process Communication (IPC).

# Installation and Configuration Instructions

This software is designed for **Windows 10/11 (64-bit)**.

### Method 1: Pre-compiled Executable (Recommended for Users)
1.  Navigate to the **Releases** section of this repository.
2.  Download the `StremioRPC.exe` file.
3.  Place the file in a dedicated folder (e.g., in Documents).
4.  Run the executable. A configuration file (`config.json`) will be generated automatically upon the first launch.
5.  (Optional) Create a shortcut in `shell:startup` to run the application automatically when Windows starts.

### Method 2: Running from Source (For Developers)
1.  Clone this repository.
2.  Ensure Python 3.10+ is installed.
3.  Install the required dependencies using the command:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the script:
    ```bash
    python main.py
    ```

# External Libraries Used

The project relies on the following third-party Python libraries:

* **pypresence:** For handling the handshake and updates with the Discord IPC.
* **requests:** For performing HTTP GET requests to both the local Stremio server and the external Cinemeta API.
* **pystray:** For creating and managing the system tray icon and menu.
* **Pillow (PIL):** For image processing required by the system tray icon.
* **pyinstaller:** Used for compiling the source code into a standalone Windows executable.

To install these manually:
```bash
pip install pypresence requests pystray Pillow pyinstaller
```

# Internal Libraries Used
* **threading:** Used to run the Stremio monitoring loop and the GUI loop concurrently without blocking.

* **json**: For parsing API responses and managing the local configuration file.

* **re:** For regular expression pattern matching and string sanitization.

* **os & sys:** For file system operations and path management across different environments (Source vs. Frozen EXE).

* **time:** For managing update intervals and heartbeat logic.

* **urllib.parse:** For encoding URL queries safely.

# Usage
The system is designed with a "Set and Forget" philosophy.

Upon execution, the application runs silently in the background. A purple satellite/link icon will appear in the Windows System Tray (near the clock).

* **Automatic Detection:** Simply open Stremio and start watching a video. The status will update automatically on Discord.

* **System Tray Menu:** Right-clicking the tray icon reveals a menu with options to:

* **View Logs:** Opens the stremio_log.txt file for debugging.

* **Exit:** Safely terminates the background process and closes the connection to Discord.

* **Configuration:** You can modify the config.json file to change the Discord Client ID, update interval, or add words to the cleanup blacklist. Changes require an application restart.

# Contributions to Consider
* **GUI for Configuration:** Develop a graphical settings window using libraries like customtkinter to allow users to modify the JSON configuration without editing the text file directly.

* **Enhanced Metadata:** Implement additional API fallbacks (e.g., TMDB or IMDB) for cases where Cinemeta might not return a result.

# License
This project is distributed under the terms of the MIT License.

The MIT License is a permissive free software license originating at the Massachusetts Institute of Technology (MIT). It puts only very limited restriction on reuse and has, therefore, an excellent license compatibility. It permits reuse within proprietary software provided that all copies of the licensed software include a copy of the MIT License terms and the copyright notice.

# Additional Resources
* **Stremio API:** https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/responses/meta.md

* **Discord RPC Documentation:** https://discord.com/developers/docs/rich-presence/how-to

* **PyInstaller Documentation:** https://pyinstaller.org/en/stable/