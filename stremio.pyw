from pypresence import Presence, ActivityType
import requests
import time
import re
import sys
import os
import json

# ---------------------------------------------------------
# TU ID AQUÍ
# ---------------------------------------------------------
client_id = "1441601634374385696"
# ---------------------------------------------------------

# --- CARGAR CONFIGURACIÓN ---
try:
    CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
    PATH_CONFIG = os.path.join(CARPETA_SCRIPT, "config.json")
    PATH_LOG = os.path.join(CARPETA_SCRIPT, "stremio_log.txt")
    
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
    PATH_LOG = "stremio_log.txt"

# --- LIMPIEZA AUTOMÁTICA DE LOGS (NUEVO V26) ---
try:
    # Si el archivo existe y pesa más de 1 MB (1024*1024 bytes)
    if os.path.exists(PATH_LOG) and os.path.getsize(PATH_LOG) > 1 * 1024 * 1024:
        # Lo abrimos en modo 'w' (write) para borrar todo su contenido
        with open(PATH_LOG, "w", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] 🧹 Log limpiado automáticamente (Superó 1MB).\n")
except:
    pass

def log(mensaje):
    texto = f"[{time.strftime('%H:%M:%S')}] {mensaje}"
    try:
        print(texto)
        with open(PATH_LOG, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except: pass

def conectar_discord():
    rpc = None
    while rpc is None:
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

# --- INICIO ---
log("🚀 Script V26.0 (Log Rotation) Iniciado...")
RPC = conectar_discord()
ultimo_titulo = ""
ultima_actualizacion = 0
tiempo_inicio_anime = None

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
                    
                    if titulo_limpio != ultimo_titulo:
                        tiempo_inicio_anime = time.time()
                    
                    if titulo_limpio != ultimo_titulo or (tiempo_actual - ultima_actualizacion > TOLERANCIA_LATIDO):
                        try:
                            RPC.update(
                                activity_type=ActivityType.WATCHING,
                                details=titulo_limpio,
                                state=None,
                                large_image="stremio_logo", 
                                large_text="Stremio",
                                start=tiempo_inicio_anime 
                            )
                            
                            ultimo_titulo = titulo_limpio
                            ultima_actualizacion = tiempo_actual
                            log(f"Actualizado: {titulo_limpio}")
                        except:
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
        log(f"Error: {e}")
        time.sleep(UPDATE_INTERVAL)

    time.sleep(UPDATE_INTERVAL)