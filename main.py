import time
import threading
import requests
import urllib.parse
import os
from pypresence import Presence, ActivityType
from pystray import Icon, MenuItem, Menu
from PIL import Image

# Importamos nuestros propios módulos
import config_manager
import utils

# Variables Globales
APP_RUNNING = True
CONFIG = config_manager.cargar_config()

def conectar_discord():
    rpc = None
    while rpc is None and APP_RUNNING:
        try:
            utils.log("Conectando a Discord...")
            rpc = Presence(CONFIG["client_id"])
            rpc.connect()
            utils.log("✅ Conectado a Discord")
        except:
            time.sleep(10)
    return rpc

def bucle_logica():
    """El cerebro del programa (Hilo secundario)"""
    global APP_RUNNING
    utils.log("🚀 Hilo Principal Iniciado (Modular).")
    
    RPC = conectar_discord()
    ultimo_titulo = ""
    ultima_actualizacion = 0
    tiempo_inicio = None
    tiempo_fin = None
    poster_actual = "stremio_logo"

    while APP_RUNNING:
        try:
            # Leer Stremio Local
            try:
                response = requests.get("http://127.0.0.1:11470/stats.json", timeout=3)
                conectado = True
            except:
                conectado = False

            if conectado and response.status_code == 200:
                data = response.json()
                
                if len(data) > 0:
                    video = list(data.values())[-1]
                    nombre_crudo = str(video.get('name', ''))
                    
                    if nombre_crudo:
                        nombre_limpio = utils.limpiar_nombre(nombre_crudo, CONFIG["blacklisted_words"])
                        tiempo_actual = time.time()
                        
                        # Stats Técnicos (Hover)
                        try:
                            total = video.get('length', 0)
                            # Fix para packs
                            if total == 0 and 'files' in video:
                                for f in video['files']:
                                    if f.get('length', 0) > total: total = f.get('length', 0)
                            
                            bajado = video.get('downloaded', 0)
                            velocidad = video.get('downSpeed', 0)
                            porcentaje = int((bajado/total)*100) if total > 0 else 0
                            stats_text = f"⬇️ {utils.formato_velocidad(velocidad)} | 💾 {porcentaje}%"
                        except:
                            stats_text = "Stremio RPC"

                        # Detectar cambio de video
                        if nombre_limpio != ultimo_titulo:
                            tiempo_inicio = time.time()
                            # Buscar Metadatos en API
                            utils.log(f"🔎 Buscando datos: {nombre_limpio}")
                            meta = utils.obtener_metadatos(nombre_limpio)
                            poster_actual = meta["poster"]
                            
                            # Calcular barra de tiempo
                            runtime = meta["runtime"]
                            if CONFIG["fixed_duration_minutes"] > 0:
                                tiempo_fin = tiempo_inicio + (CONFIG["fixed_duration_minutes"] * 60)
                            elif runtime > 0:
                                tiempo_fin = tiempo_inicio + (runtime * 60)
                            else:
                                tiempo_fin = None

                        # Actualizar Discord
                        if nombre_limpio != ultimo_titulo or (tiempo_actual - ultima_actualizacion > 15):
                            try:
                                url_btn = f"https://www.google.com/search?q={urllib.parse.quote(nombre_limpio)}+anime"
                                RPC.update(
                                    activity_type=ActivityType.WATCHING,
                                    details=nombre_limpio,
                                    state=None, # Minimalista
                                    large_image=poster_actual,
                                    large_text=stats_text,
                                    start=tiempo_inicio,
                                    end=tiempo_fin,
                                    buttons=[{"label": "Buscar Anime 🔎", "url": url_btn}]
                                )
                                ultimo_titulo = nombre_limpio
                                ultima_actualizacion = tiempo_actual
                                utils.log(f"Actualizado: {nombre_limpio}")
                            except:
                                RPC = conectar_discord()
                else:
                    pass # Anti-Buffer activo
            else:
                if ultimo_titulo != "":
                    try:
                        RPC.clear()
                        ultimo_titulo = ""
                        utils.log("❌ Stremio cerrado.")
                    except: pass

        except Exception as e:
            utils.log(f"Error Loop: {e}")
            time.sleep(CONFIG["update_interval"])
        
        time.sleep(CONFIG["update_interval"])

    try: RPC.close() 
    except: pass

# --- GUI TRAY (Hilo Principal) ---
def salir(icon, item):
    global APP_RUNNING
    APP_RUNNING = False
    icon.stop()

def abrir_logs(icon, item):
    os.startfile(config_manager.PATH_LOG)

if __name__ == '__main__':
    utils.gestionar_logs()
    
    # Iniciar hilo lógico
    hilo = threading.Thread(target=bucle_logica)
    hilo.daemon = True
    hilo.start()
    
    # Iniciar GUI
    try:
        if os.path.exists(config_manager.PATH_ICON):
            img = Image.open(config_manager.PATH_ICON)
            menu = Menu(MenuItem('Ver Logs', abrir_logs), MenuItem('Salir', salir))
            icon = Icon("StremioRPC", img, "Stremio RPC", menu)
            icon.run()
        else:
            while APP_RUNNING: time.sleep(1)
    except:
        while APP_RUNNING: time.sleep(1)