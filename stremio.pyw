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
    DURACION_FIJA = config.get("fixed_duration_minutes", 0)
except:
    CLIENT_ID = client_id
    UPDATE_INTERVAL = 5
    PALABRAS_BASURA = []
    TOLERANCIA_LATIDO = 60
    DURACION_FIJA = 0

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

# --- FUNCIÓN DE LIMPIEZA MEJORADA (V31) ---
def limpiar_nombre(nombre_crudo):
    nombre_limpio = nombre_crudo
    
    # 1. Reemplazar puntos por espacios (Fallout.S01 -> Fallout S01)
    nombre_limpio = nombre_limpio.replace(".", " ")
    
    # 2. Quitar corchetes y parentesis
    nombre_limpio = re.sub(r'\[.*?\]', '', nombre_limpio)
    nombre_limpio = re.sub(r'\(.*?\)', '', nombre_limpio)
    
    # 3. Quitar palabras basura
    for basura in PALABRAS_BASURA:
        # Usamos regex con \b para asegurar que borre palabras completas
        # y evitar borrar letras dentro de otras palabras
        nombre_limpio = re.sub(r'\b' + re.escape(basura) + r'\b', '', nombre_limpio, flags=re.IGNORECASE)
        # Respaldo simple por si acaso
        nombre_limpio = re.sub(basura, '', nombre_limpio, flags=re.IGNORECASE)
    
    # 4. Limpieza final de extensiones y espacios dobles
    nombre_limpio = nombre_limpio.replace("mkv", "").replace("mp4", "").replace("avi", "")
    # Reemplazar múltiples espacios por uno solo
    nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio).strip()
    nombre_limpio = nombre_limpio.strip(".-_ ")

    if not nombre_limpio: nombre_limpio = "Stremio"
    return nombre_limpio

def formato_velocidad(bytes_sec):
    try:
        if bytes_sec > 1024 * 1024:
            return f"{bytes_sec / (1024 * 1024):.1f} MB/s"
        elif bytes_sec > 1024:
            return f"{bytes_sec / 1024:.0f} KB/s"
        else:
            return "0 KB/s"
    except:
        return "0 KB/s"

def bucle_principal():
    global APP_RUNNING
    log("🚀 Hilo V31.0 (Deep Clean) iniciado.")
    RPC = conectar_discord()
    ultimo_titulo = ""
    ultima_actualizacion = 0
    tiempo_inicio_anime = None
    tiempo_fin_estimado = None

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
                    
                    try:
                        total_bytes = video_actual.get('length', 0)
                        if total_bytes == 0 and 'files' in video_actual:
                            for f in video_actual['files']:
                                if f.get('length', 0) > total_bytes:
                                    total_bytes = f.get('length', 0)

                        descargado_bytes = video_actual.get('downloaded', 0)
                        velocidad_bytes = video_actual.get('downSpeed', 0)
                        
                        porcentaje = 0
                        if total_bytes > 0:
                            porcentaje = int((descargado_bytes / total_bytes) * 100)
                        
                        velocidad_str = formato_velocidad(velocidad_bytes)
                        texto_tecnico = f"⬇️ {velocidad_str} | 💾 {porcentaje}%"
                    except:
                        texto_tecnico = "Stremio"

                    if nombre_crudo:
                        titulo_limpio = limpiar_nombre(nombre_crudo)
                        tiempo_actual = time.time()
                        
                        if titulo_limpio != ultimo_titulo:
                            tiempo_inicio_anime = time_now = time.time()
                            if DURACION_FIJA > 0:
                                tiempo_fin_estimado = time_now + (DURACION_FIJA * 60)
                            else:
                                tiempo_fin_estimado = None
                        
                        if titulo_limpio != ultimo_titulo or (tiempo_actual - ultima_actualizacion > 15):
                            try:
                                url_busqueda = f"https://www.google.com/search?q={urllib.parse.quote(titulo_limpio)}+anime"
                                
                                RPC.update(
                                    activity_type=ActivityType.WATCHING,
                                    details=titulo_limpio,
                                    state=None,
                                    large_image="stremio_logo", 
                                    large_text=texto_tecnico,
                                    start=tiempo_inicio_anime,
                                    end=tiempo_fin_estimado,
                                    buttons=[{"label": "Buscar Anime 🔎", "url": url_busqueda}]
                                )
                                ultimo_titulo = titulo_limpio
                                ultima_actualizacion = tiempo_actual
                                log(f"Actualizado: {titulo_limpio} ({texto_tecnico})")
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