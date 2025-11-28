import subprocess
import json
import logging
import os
import sys

import config_manager

# Path to the PowerShell script
SCRIPT_PATH = os.path.join(config_manager.ASSET_DIR, "get_media_info.ps1")

def get_media_info():
    """
    Calls the PowerShell script to get Windows Media Controls info.
    Returns a dict with title, artist, status, etc.
    """
    try:
        # Run PowerShell script
        # We use -ExecutionPolicy Bypass to ensure it runs
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", SCRIPT_PATH]
        
        # Hide window on Windows
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', # Force UTF-8 for special chars
            errors='replace', # [NUEVO] Evitar crash si hay caracteres raros
            startupinfo=startupinfo,
            creationflags=0x08000000, # CREATE_NO_WINDOW
            timeout=5 # Fast timeout
        )

        if result.returncode != 0:
            # logging.error(f"PowerShell Error: {result.stderr}")
            return None

        if not result.stdout:
            return None

        output = result.stdout.strip()
        if not output:
            return None

        # Parse JSON
        data = json.loads(output)
        
        # Check if we have valid data
        if not data.get("title"):
            return None

        # Map to our format
        source_id = data.get("source", "")
        
        # [FILTRO] Solo permitir YouTube Music (PWA)
        # El ID suele ser algo como: music.youtube.com-5929F88E...
        if "music.youtube.com" not in source_id.lower():
            # logging.info(f"Ignorando fuente: {source_id}")
            return None

        return {
            "title": data.get("title"),
            "artist": data.get("artist"),
            "is_playing": data.get("status") == "Playing",
            "status": data.get("status"),
            "source": source_id,
            "album_title": "YouTube Music", 
            "cover_url": None 
        }

    except Exception as e:
        logging.error(f"Error in smtc_manager: {e}")
        return None
