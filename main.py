import time
import threading
import logging
from logging.handlers import RotatingFileHandler
from pystray import Icon, MenuItem, Menu
from PIL import Image
import os
import sys

import config_manager
import utils
import gui
from client import StremioRPCClient

# [FIX] Forzar UTF-8 en consola Windows para evitar errores con emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURACIÓN DE LOGGING ---
class CustomFormatter(logging.Formatter):
    def format(self, record):
        original_msg = record.msg
        if record.levelno == logging.INFO:
            if not any(e in str(original_msg) for e in ["✅", "🚀", "🔎", "♻️", "🗑️", "⚠️", "❌", "ℹ️", "🔌"]):
                record.msg = f"ℹ️ {original_msg}"
        elif record.levelno == logging.WARNING:
            if "⚠️" not in str(original_msg):
                record.msg = f"⚠️ {original_msg}"
        elif record.levelno >= logging.ERROR:
            if "❌" not in str(original_msg):
                record.msg = f"❌ {original_msg}"
        
        result = super().format(record)
        record.msg = original_msg
        return result

# Cargar configuración
config = config_manager.cargar_config()
log_size = config.get("log_max_size_mb", 1) * 1024 * 1024
log_backups = config.get("log_backup_count", 3)

formatter = CustomFormatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')

# File Handler
file_handler = RotatingFileHandler(
    config_manager.PATH_LOG, 
    maxBytes=log_size, 
    backupCount=log_backups, 
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

# Stream Handler (Consola)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler],
    force=True
)

# Silenciar warnings de conexión de urllib3 (requests)
logging.getLogger("urllib3").setLevel(logging.ERROR)

def exit_app(icon, item, client):
    client.stop()
    icon.stop()

def open_logs(icon, item):
    if os.path.exists(config_manager.PATH_LOG):
        os.startfile(config_manager.PATH_LOG)

def restart_rpc_tray(icon, item):
    flag_path = os.path.join(os.path.dirname(config_manager.PATH_CONFIG), "rpc_restart.flag")
    with open(flag_path, "w") as f:
        f.write("restart")

def open_config(icon, item):
    import subprocess
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, "gui"])
    else:
        subprocess.Popen([sys.executable, "gui.py"])

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        gui.abrir_ventana()
        sys.exit()

    # [NUEVO] Single Instance Check (Mutex)
    # Evita que se abran múltiples instancias
    import ctypes
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "Global\\MediaRPC_Instance_Mutex_v5")
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        logging.error("❌ Otra instancia ya está corriendo. Cerrando...")
        sys.exit(0)
    
    # [NUEVO] Chequeo de actualizaciones
    CURRENT_VERSION = "v5.5.1"
    has_update, new_version = utils.check_for_updates(CURRENT_VERSION)
    if has_update:
        logging.warning(f"⚠️ ¡Nueva versión disponible: {new_version}!")
        logging.warning(f"Descárgala en: https://github.com/anthonybuitrago/stremio-discord-rpc/releases")

    client = StremioRPCClient()
    
    thread = threading.Thread(target=client.run_logic)
    thread.daemon = True
    thread.start()
    
    try:
        if os.path.exists(config_manager.PATH_ICON):
            img = Image.open(config_manager.PATH_ICON)
            menu = Menu(
                MenuItem('⚙️ Configuración', open_config),
                MenuItem('💻 Iniciar con Windows', utils.toggle_autostart, checked=lambda item: utils.check_autostart()),
                MenuItem('📂 Abrir Logs', open_logs),
                MenuItem('♻️ Reiniciar RPC', restart_rpc_tray),
                MenuItem('❌ Salir', lambda icon, item: exit_app(icon, item, client))
            )
            icon = Icon("MediaRPC", img, "Media RPC", menu)
            icon.run()
        else:
            while client.running: time.sleep(1)
    except KeyboardInterrupt:
        client.stop()
    except Exception as e:
        logging.critical(f"Error fatal: {e}")
        while client.running: time.sleep(1)
