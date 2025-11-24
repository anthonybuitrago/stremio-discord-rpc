from pypresence import Presence, ActivityType
import requests
import time
import re
import sys
import os
import json
import threading
import urllib.parse
from pystray import Icon, MenuItem, Menu
from PIL import Image

# ---------------------------------------------------------
# TU ID AQUÍ
# ---------------------------------------------------------
client_id = "1441601634374385696"
# ---------------------------------------------------------

APP_RUNNING = True 

if getattr(sys, 'frozen', False):
    CARPETA_SCRIPT = os.path.dirname(sys.executable)
else:
    CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

PATH_CONFIG = os.path.join(CARPETA_SCRIPT, "config.json")
PATH_LOG = os.path.join(CARPETA_SCRIPT, "stremio_log.txt")
PATH_ICON = os.path.join(CARPETA_SCRIPT, "rpc.ico")

# --- CONFIG ---
try:
    with open(PATH_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    CLIENT_ID = config.get("client_id", client_id)
    UPDATE_INTERVAL = config.get("update_interval", 5)
    TOLERANCIA_LATIDO = config.get("tolerance_seconds", 60)
    PALABRAS_BASURA = config.get("blacklisted_words", [])
except:
    CLIENT_ID = client_id
    UPDATE_INTERVAL = 5
    PALABRAS_BASURA = []
    TOLERANCIA_LATIDO = 60

# Limpieza logs
try:
    if os.path.exists(PATH_LOG) and os.path.getsize(PATH_LOG) > 1 * 1024 * 1024:
        with open(PATH_LOG, "w", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] 🧹 Log limpiado.\n")
except: pass

def log(mensaje):
    texto = f"[{time.strftime('%H:%M:%S')}] {mensaje}"
    try:
        print(texto)
        with open(PATH_LOG, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except: pass

def conectar_discord():
    rpc = None
    while rpc is None and APP_RUNNING:
        try:
            log("Conectando a Discord...")
            rpc = Presence(CLIENT_ID)
            rpc.connect()
            log("✅ Conectado a Discord")
        except:
            time.sleep(10)
    return rpc

def limpiar_nombre(nombre_crudo):
    nombre_limpio = nombre_crudo
    nombre_limpio = re.sub(r'\[.*?\]', '', nombre_limpio)
    nombre_limpio = re.sub(r'\(.*?\)', '', nombre_limpio)
    for basura in PALABRAS_BASURA:
        nombre_limpio = re.sub(basura, '', nombre_limpio, flags=re.IGNORECASE)
    nombre_limpio = nombre_limpio.replace(".mkv", "").replace(".mp4", "").replace("  ", " ").strip()
    nombre_limpio = nombre_limpio.strip(".-_ ")
    if not nombre_limpio: nombre_limpio = "Stremio"
    return nombre_limpio

# --- SOLO BUSCAMOS EL PÓSTER ---
def obtener_poster(nombre_limpio):
    if nombre_limpio == "Stremio": return "stremio_logo"
    
    try:
        query = urllib.parse.quote(nombre_limpio)
        
        # Intentamos Serie
        url_series = f"https://v3-cinemeta.strem.io/catalog/series/top/search={query}.json"
        resp = requests.get(url_series, timeout=2)
        data = resp.json()
        
        if 'metas' in data and len(data['metas']) > 0:
            return data['metas'][0].get('poster', 'stremio_logo')
        
        # Intentamos Peli
        url_movie = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={query}.json"
        resp_mov = requests.get(url_movie, timeout=2)
        data_mov = resp_mov.json()
        
        if 'metas' in data_mov and len(data_mov['metas']) > 0:
            return data_mov['metas'][0].get('poster', 'stremio_logo')

    except Exception as e:
        log(f"⚠️ Error Poster: {e}")
    
    return "stremio_logo"

def bucle_principal():
    global APP_RUNNING
    log("🚀 Hilo V35.0 (Final Aesthetic) iniciado.")
    RPC = conectar_discord()
    ultimo_titulo = ""
    ultima_actualizacion = 0
    tiempo_inicio_anime = None
    
    cache_poster = "stremio_logo"

    while APP_RUNNING:
        try:
            try:
                response = requests.get("http://127.0.0.1:11470/stats.json", timeout=3)
                stremio_conectado = True
            except:
                stremio_conectado = False

            if stremio_conectado and response.status_code == 200:
                data = response.json()
                
                if len(data) > 0:
                    video_actual = list(data.values())[-1]
                    nombre_crudo = str(video_actual.get('name', ''))
                    
                    if nombre_crudo:
                        titulo_limpio = limpiar_nombre(nombre_crudo)
                        tiempo_actual = time.time()
                        
                        if titulo_limpio != ultimo_titulo:
                            tiempo_inicio_anime = time.time()
                            log(f"🔎 Buscando póster para: {titulo_limpio}")
                            cache_poster = obtener_poster(titulo_limpio)

                        if titulo_limpio != ultimo_titulo or (tiempo_actual - ultima_actualizacion > 15):
                            try:
                                url_busqueda = f"https://www.google.com/search?q={urllib.parse.quote(titulo_limpio)}+anime"
                                
                                RPC.update(
                                    activity_type=ActivityType.WATCHING,
                                    details=titulo_limpio,
                                    state=None, # <--- SEGUNDA LÍNEA SIEMPRE VACÍA
                                    large_image=cache_poster, 
                                    large_text="Stremio",
                                    start=tiempo_inicio_anime,
                                    buttons=[{"label": "Buscar Anime 🔎", "url": url_busqueda}]
                                )
                                ultimo_titulo = titulo_limpio
                                ultima_actualizacion = tiempo_actual
                                log(f"Actualizado: {titulo_limpio}")
                            except Exception as e_discord:
                                log(f"🔥 Error Discord: {e_discord}")
                                RPC = conectar_discord()
                else:
                    pass 
            else:
                if ultimo_titulo != "":
                    try:
                        RPC.clear()
                        ultimo_titulo = ""
                        log("❌ Stremio cerrado.")
                    except: pass

        except Exception as e:
            log(f"Error General: {e}")
            time.sleep(UPDATE_INTERVAL)

        time.sleep(UPDATE_INTERVAL)
    
    try: RPC.close()
    except: pass
    log("👋 Hilo finalizado.")

def salir_app(icon, item):
    global APP_RUNNING
    log("🛑 Cerrando...")
    APP_RUNNING = False
    icon.stop()

def abrir_log(icon, item):
    os.startfile(PATH_LOG)

if __name__ == '__main__':
    hilo_stremio = threading.Thread(target=bucle_principal)
    hilo_stremio.daemon = True
    hilo_stremio.start()

    try:
        if os.path.exists(PATH_ICON):
            image = Image.open(PATH_ICON)
            menu = Menu(MenuItem('Ver Logs 📄', abrir_log), MenuItem('Salir ❌', salir_app))
            icon = Icon("StremioRPC", image, "Stremio RPC", menu)
            icon.run()
        else:
            while APP_RUNNING: time.sleep(1)
    except:
        while APP_RUNNING: time.sleep(1)