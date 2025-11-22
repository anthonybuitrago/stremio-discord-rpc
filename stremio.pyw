from pypresence import Presence
import requests
import time
import re

# ---------------------------------------------------------
# TU ID AQUÍ
# ---------------------------------------------------------
client_id = "1441601634374385696"
# ---------------------------------------------------------

# Esperamos a que Discord abra
RPC = None
while RPC is None:
    try:
        RPC = Presence(client_id)
        RPC.connect()
    except:
        time.sleep(10)

ultimo_video = ""

# LISTA NEGRA DE PALABRAS (Case Insensitive)
# Aquí puedes agregar cualquier cosa que quieras borrar del título
palabras_basura = [
    "1080p", "720p", "480p", "4k", "2160p", 
    "hdrip", "web-dl", "bluray", "x265", "hevc", 
    "aac", "h264", "webrip"
]

while True:
    try:
        response = requests.get("http://127.0.0.1:11470/stats.json")
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                video_actual = list(data.values())[-1]
                nombre_crudo = str(video_actual.get('name', ''))
                
                if nombre_crudo:
                    # --- FASE 1: RegEx (Estructuras) ---
                    # Quitamos todo lo que esté entre corchetes [Texto]
                    nombre_limpio = re.sub(r'\[.*?\]', '', nombre_crudo)
                    # Quitamos todo lo que esté entre paréntesis (Texto) -> Adiós al año (2025)
                    nombre_limpio = re.sub(r'\(.*?\)', '', nombre_limpio)

                    # --- FASE 2: Palabras Sueltas ---
                    # Barremos la lista negra
                    for basura in palabras_basura:
                        # re.IGNORECASE hace que borre '1080p', '1080P', '1080P' etc.
                        nombre_limpio = re.sub(basura, '', nombre_limpio, flags=re.IGNORECASE)

                    # --- FASE 3: Pulido Final ---
                    # Quitamos extensiones y espacios extra que hayan quedado
                    nombre_limpio = nombre_limpio.replace(".mkv", "").replace(".mp4", "")
                    # Quitamos caracteres raros que a veces quedan sueltos como guiones dobles
                    nombre_limpio = nombre_limpio.replace("  ", " ").strip() 
                    
                    # Si borramos tanto que no quedó nada, volvemos al original por seguridad
                    if not nombre_limpio: nombre_limpio = nombre_crudo

                    if nombre_limpio != ultimo_video:
                        RPC.update(details=nombre_limpio, large_image="stremio_logo", large_text="Stremio")
                        ultimo_video = nombre_limpio
                else:
                    pass
            else:
                RPC.clear()
                ultimo_video = ""
    except:
        pass

    time.sleep(8)