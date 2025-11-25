import json
import os
import sys

# --- RUTAS DEL SISTEMA ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATH_CONFIG = os.path.join(BASE_DIR, "config.json")
PATH_LOG = os.path.join(BASE_DIR, "stremio_log.txt")
PATH_ICON = os.path.join(BASE_DIR, "assets", "rpc.ico")

# --- CONFIGURACIÓN POR DEFECTO V5 ---
DEFAULT_CONFIG = {
    "client_id": "1441601634374385696",
    "update_interval": 5,
    "tolerance_seconds": 60,
    "show_search_button": True,     # Control del Botón
    "fixed_duration_minutes": 0     # 0 = Auto/Real, 24 = Anime
}

def cargar_config():
    """Carga la configuración desde el JSON o crea uno nuevo si no existe."""
    try:
        if not os.path.exists(PATH_CONFIG):
            print(f"⚠️ Config no encontrada. Creando nueva en: {PATH_CONFIG}")
            guardar_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
            
        with open(PATH_CONFIG, "r", encoding="utf-8") as f:
            datos = json.load(f)
            # Fusionar con default para asegurar integridad
            config_final = DEFAULT_CONFIG.copy()
            config_final.update(datos)
            return config_final

    except json.JSONDecodeError as e:
        print(f"❌ ERROR CRÍTICO: Config corrupta. {e}")
        return DEFAULT_CONFIG
    except Exception as e:
        print(f"❌ Error leyendo config: {e}")
        return DEFAULT_CONFIG

def guardar_config(datos):
    """Guarda el diccionario en el archivo JSON."""
    try:
        with open(PATH_CONFIG, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)
    except Exception as e:
        print(f"❌ Error guardando config: {e}")