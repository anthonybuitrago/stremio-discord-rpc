from pypresence import Presence, ActivityType
import requests
import time
import re
import sys
import os
import urllib.parse

# ---------------------------------------------------------
# TU ID AQUÍ
# ---------------------------------------------------------
client_id = "1441601634374385696"
# ---------------------------------------------------------

try:
    CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
    ARCHIVO_LOG = os.path.join(CARPETA_SCRIPT, "stremio_log.txt")
except:
    CARPETA_SCRIPT = ""
    ARCHIVO_LOG = "stremio_log.txt"

def log(mensaje):
    texto = f"[{time.strftime('%H:%M:%S')}] {mensaje}"
    try:
        print(texto)
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except: pass

# Lista de palabras a eliminar del título
palabras_basura = [
    "1080p", "720p", "480p", "4k", "2160p", "hdrip", "web-dl", "bluray", 
    "x265", "hevc", "aac", "h264", "webrip", "dual audio", "10bit", 
    "anime time", "eng sub"
]

def conectar_discord():
    rpc = None
    while rpc is None:
        try:
            log("Conectando a Discord...")
            rpc = Presence(client_id)
            rpc.connect()
            log("✅ Conectado a Discord")
        except:
            time.sleep(10)
    return rpc

def limpiar_nombre(nombre_crudo):
    nombre_limpio = nombre_crudo
    
    # 1. Quitar contenido entre corchetes [] y paréntesis ()
    nombre_limpio = re.sub(r'\[.*?\]', '', nombre_limpio)
    nombre_limpio = re.sub(r'\(.*?\)', '', nombre_limpio)
    
    # 2. Quitar palabras técnicas
    for basura in palabras_basura:
        nombre_limpio = re.sub(basura, '', nombre_limpio, flags=re.IGNORECASE)
    
    # 3. Limpieza final de extensiones y espacios
    nombre_limpio = nombre_limpio.replace(".mkv", "").replace(".mp4", "").replace("  ", " ").strip()
    nombre_limpio = nombre_limpio.strip(".-_ ")

    if not nombre_limpio: nombre_limpio = "Stremio"
    
    return nombre_limpio

# --- INICIO ---
log("🚀 Script V18.0 (Clean Minimalist) Iniciado...")
RPC = conectar_discord()
ultimo_titulo = ""
ultima_actualizacion = 0

while True:
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
                    
                    # Actualizamos si cambió el título o para mantener latido
                    if titulo_limpio != ultimo_titulo or (tiempo_actual - ultima_actualizacion > 60):
                        try:
                            # Generar URL del botón
                            url_busqueda = f"https://www.google.com/search?q={urllib.parse.quote(titulo_limpio)}+anime"

                            RPC.update(
                                activity_type=ActivityType.WATCHING, # Icono de TV
                                details=titulo_limpio, # Solo el nombre limpio
                                state=None, # Dejamos la línea de abajo vacía
                                large_image="stremio_logo", 
                                large_text="Stremio",
                                buttons=[{"label": "Buscar Anime 🔎", "url": url_busqueda}]
                            )
                            
                            ultimo_titulo = titulo_limpio
                            ultima_actualizacion = tiempo_actual
                            log(f"Actualizado: {titulo_limpio}")
                        except:
                            RPC = conectar_discord()
            else:
                pass # Mantenemos estado (Cache-Proof)
        else:
            if ultimo_titulo != "":
                try:
                    RPC.clear()
                    ultimo_titulo = ""
                    log("❌ Stremio cerrado.")
                except: pass

    except Exception as e:
        log(f"Error: {e}")
        time.sleep(5)

    time.sleep(5)