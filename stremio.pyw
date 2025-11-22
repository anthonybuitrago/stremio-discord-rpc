from pypresence import Presence
import requests
import time
import re
import sys
import os

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

palabras_basura = ["1080p", "720p", "480p", "4k", "2160p", "hdrip", "web-dl", "bluray", "x265", "hevc", "aac", "h264", "webrip"]

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

# --- INICIO ---
log("🚀 Script V14.0 (Cache-Proof) Iniciado...")
RPC = conectar_discord()
ultimo_video = ""
ultima_actualizacion = 0

while True:
    try:
        # INTENTO DE CONEXIÓN CON STREMIO
        try:
            response = requests.get("http://127.0.0.1:11470/stats.json", timeout=3)
            # Si llegamos aquí, Stremio ESTÁ ABIERTO (aunque mande datos vacíos)
            stremio_conectado = True
        except:
            # Si salta al except, Stremio ESTÁ CERRADO O APAGADO
            stremio_conectado = False

        if stremio_conectado and response.status_code == 200:
            data = response.json()
            
            if len(data) > 0:
                # --- ESCENARIO 1: STREMIO DESCARGANDO/REPRODUCIENDO ---
                video_actual = list(data.values())[-1]
                nombre_crudo = str(video_actual.get('name', ''))
                
                if nombre_crudo:
                    nombre_limpio = re.sub(r'\[.*?\]', '', nombre_crudo)
                    nombre_limpio = re.sub(r'\(.*?\)', '', nombre_limpio)
                    for basura in palabras_basura:
                        nombre_limpio = re.sub(basura, '', nombre_limpio, flags=re.IGNORECASE)
                    nombre_limpio = nombre_limpio.replace(".mkv", "").replace(".mp4", "").replace("  ", " ").strip()
                    if not nombre_limpio: nombre_limpio = nombre_crudo

                    tiempo_actual = time.time()
                    
                    # Actualizamos si cambió el nombre o para mantener el latido
                    if nombre_limpio != ultimo_video or (tiempo_actual - ultima_actualizacion > 60):
                        try:
                            RPC.update(details=nombre_limpio, large_image="stremio_logo", large_text="Stremio")
                            ultimo_video = nombre_limpio
                            ultima_actualizacion = tiempo_actual
                            log(f"Actualizado: {nombre_limpio}")
                        except:
                            RPC = conectar_discord()
            else:
                # --- ESCENARIO 2: STREMIO VACÍO (VIDEO EN CACHÉ / BUFFER 100%) ---
                # AQUÍ ESTÁ EL CAMBIO:
                # No hacemos NADA. No limpiamos. Asumimos que sigues viendo lo último.
                # log("Stremio abierto pero sin datos (Posible caché). Manteniendo estado.") 
                pass

        else:
            # --- ESCENARIO 3: STREMIO CERRADO (APP MUERTA) ---
            # Solo aquí borramos el estado.
            if ultimo_video != "":
                try:
                    RPC.clear()
                    ultimo_video = ""
                    log("❌ Stremio cerrado. Estado limpiado.")
                except: pass

    except Exception as e:
        log(f"Error: {e}")
        time.sleep(5)

    time.sleep(5)