import json
import os
import sys

# --- RUTAS DEL SISTEMA ---
# Detectamos si estamos corriendo como script o como .exe congelado
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATH_CONFIG = os.path.join(BASE_DIR, "config.json")
PATH_LOG = os.path.join(BASE_DIR, "stremio_log.txt")
PATH_ICON = os.path.join(BASE_DIR, "assets", "rpc.ico")

# --- CONFIGURACIÓN POR DEFECTO ---
# Esto se usa si el archivo JSON no existe o falla
DEFAULT_CONFIG = {
    "client_id": "1441601634374385696",
    "update_interval": 5,
    "tolerance_seconds": 60,
    "blacklisted_words": [
        "1080p", "720p", "480p", "4k", "2160p", "hdrip", "web-dl", "bluray",
        "x265", "hevc", "aac", "h264", "webrip", "dual audio", "10bit",
        "anime time", "eng sub"
    ],
    "fixed_duration_minutes": 0
}

def cargar_config():
    """Carga la configuración desde el JSON o crea uno nuevo si no existe."""
    try:
        if not os.path.exists(PATH_CONFIG):
            guardar_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
            
        with open(PATH_CONFIG, "r", encoding="utf-8") as f:
            datos = json.load(f)
            # Mezclamos con default para asegurar que no falten claves
            config_final = DEFAULT_CONFIG.copy()
            config_final.update(datos)
            return config_final
    except:
        return DEFAULT_CONFIG

def guardar_config(datos):
    """Guarda el diccionario actual en el archivo JSON."""
    try:
        with open(PATH_CONFIG, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)
    except:
        pass