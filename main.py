import time
import threading
import requests
import urllib.parse
import logging
from logging.handlers import RotatingFileHandler
from pypresence import Presence, ActivityType
from pystray import Icon, MenuItem, Menu
from PIL import Image
import os
import sys

import config_manager
import utils
import gui

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

class StremioRPCClient:
    def __init__(self):
        self.running = True
        self.config = config_manager.cargar_config()
        self.rpc = None
        self.last_title = ""
        self.last_update = 0
        self.start_time = None
        self.end_time = None
        self.current_poster = "stremio_logo"
        self.official_title = ""
        
    def connect_discord(self):
        self.rpc = None
        while self.rpc is None and self.running:
            try:
                logging.info("Conectando a Discord...")
                self.rpc = Presence(self.config["client_id"])
                self.rpc.connect()
                logging.info("✅ Conectado a Discord")
            except Exception as e:
                logging.error(f"Error conectando a Discord: {e}")
                time.sleep(10)
        return self.rpc

    def _fetch_stremio_data(self):
        """Intenta obtener datos de Stremio. Retorna (connected, data)."""
        try:
            # Usamos la sesión robusta de utils
            session = utils.get_robust_session()
            response = session.get("http://127.0.0.1:11470/stats.json", timeout=3)
            if response.status_code == 200:
                return True, response.json()
        except requests.RequestException:
            pass
        return False, {}

    def _process_video_stats(self, video):
        """Calcula estadísticas de descarga."""
        try:
            total = float(video.get("total", 0))
            downloaded = float(video.get("downloaded", 0))
            if total > 0:
                percentage = (downloaded / total) * 100
                return f"💾 {percentage:.0f}%"
        except:
            pass
        return "Stremio"

    def _update_rpc(self, clean_name, video_type, stats_text):
        """Actualiza la presencia de Discord si es necesario."""
        current_time = time.time()

        # Si cambió el título, buscamos nuevos metadatos
        if clean_name != self.last_title:
            self.last_title = clean_name
            
            logging.info(f"🔎 API: {clean_name} ({video_type})")
            meta = utils.obtener_metadatos(clean_name, video_type)
            
            self.current_poster = meta["poster"]
            self.official_title = meta["name"]

        # Actualizamos RPC cada 15 segundos
        if current_time - self.last_update > 15:
            try:
                buttons_list = None
                if self.config.get("show_search_button", True):
                    url_btn = f"https://www.google.com/search?q={urllib.parse.quote(self.official_title)}+anime"
                    buttons_list = [{"label": "Buscar Anime 🔎", "url": url_btn}]

                self.rpc.update(
                    activity_type=ActivityType.WATCHING,
                    details=self.official_title,
                    state=None,
                    large_image=self.current_poster,
                    large_text=stats_text,
                    buttons=buttons_list
                )
                self.last_update = current_time
            except Exception as e:
                logging.error(f"Error actualizando RPC: {e}")
                self.connect_discord()

    def _clear_rpc(self):
        """Limpia la presencia si Stremio se detuvo."""
        if self.last_title != "":
            try:
                # [MODIFICADO] Antes de limpiar, verificamos si el proceso sigue vivo.
                # Verificamos múltiples nombres de proceso para cubrir diferentes versiones.
                if (utils.is_process_running("stremio.exe") or 
                    utils.is_process_running("stremio-runtime.exe") or 
                    utils.is_process_running("stremio-shell-ng.exe")):
                    logging.info("⚠️ API desconectada pero Stremio sigue abierto. Manteniendo RPC.")
                    return

                self.rpc.clear()
                self.last_title = ""
                logging.info("❌ Stremio cerrado.")
            except Exception: pass

    def run_logic(self):
        logging.info("🚀 Stremio RPC v5.2 Iniciado")
        self.connect_discord()

        while self.running:
            # 1. Recargar Configuración Dinámica
            self.config = config_manager.cargar_config()

            # 2. Chequear Flag de Reinicio
            flag_path = os.path.join(os.path.dirname(config_manager.PATH_CONFIG), "rpc_restart.flag")
            if os.path.exists(flag_path):
                logging.info("♻️ Reiniciando RPC a petición del usuario...")
                try:
                    if self.rpc: self.rpc.close()
                    os.remove(flag_path)
                except: pass
                self.connect_discord()

            try:
                connected, data = self._fetch_stremio_data()

                if connected and len(data) > 0:
                    video = list(data.values())[-1]
                    raw_name = str(video.get('name', ''))
                    
                    if raw_name:
                        clean_name, video_type = utils.extraer_datos_video(raw_name)
                        if clean_name:
                            stats_text = self._process_video_stats(video)
                            self._update_rpc(clean_name, video_type, stats_text)
                    else:
                        # Stremio abierto pero sin reproducir nada
                        pass
                else:
                    self._clear_rpc()

            except Exception as e:
                logging.error(f"Error Loop: {e}")
                time.sleep(self.config["update_interval"])
            
            time.sleep(self.config["update_interval"])

        try: 
            if self.rpc: self.rpc.close() 
        except Exception: pass

    def stop(self):
        self.running = False

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
            icon = Icon("StremioRPC", img, "Stremio", menu)
            icon.run()
        else:
            while client.running: time.sleep(1)
    except KeyboardInterrupt:
        client.stop()
    except Exception as e:
        logging.critical(f"Error fatal: {e}")
        while client.running: time.sleep(1)
