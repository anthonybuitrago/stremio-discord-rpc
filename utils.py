import time
import re
import requests
import urllib.parse
import os
from config_manager import PATH_LOG

def log(mensaje):
    """Escribe mensajes en el archivo de registro y en consola."""
    texto = f"[{time.strftime('%H:%M:%S')}] {mensaje}"
    try:
        print(texto)
        with open(PATH_LOG, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except: pass

def gestionar_logs():
    """Limpia el archivo de log si es demasiado grande (>1MB)."""
    try:
        if os.path.exists(PATH_LOG) and os.path.getsize(PATH_LOG) > 1 * 1024 * 1024:
            with open(PATH_LOG, "w", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] 🧹 Log limpiado automáticamente.\n")
    except: pass

def limpiar_nombre(nombre_crudo, lista_negra):
    """Limpia el nombre del archivo usando la lista negra."""
    nombre = nombre_crudo.replace(".", " ")
    nombre = re.sub(r'\[.*?\]', '', nombre)
    nombre = re.sub(r'\(.*?\)', '', nombre)
    
    for basura in lista_negra:
        nombre = re.sub(r'\b' + re.escape(basura) + r'\b', '', nombre, flags=re.IGNORECASE)
        nombre = re.sub(basura, '', nombre, flags=re.IGNORECASE)
    
    nombre = nombre.replace("mkv", "").replace("mp4", "").replace("avi", "")
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    nombre = nombre.strip(".-_ ")

    return nombre if nombre else "Stremio"

def formato_velocidad(bytes_sec):
    """Convierte bytes/s a MB/s o KB/s legible."""
    try:
        if bytes_sec > 1024 * 1024:
            return f"{bytes_sec / (1024 * 1024):.1f} MB/s"
        elif bytes_sec > 1024:
            return f"{bytes_sec / 1024:.0f} KB/s"
        else:
            return "0 KB/s"
    except: return "0 KB/s"

def extraer_minutos(texto_runtime):
    """Intenta sacar el número de minutos de un texto como '124 min'."""
    try:
        numeros = re.findall(r'\d+', str(texto_runtime))
        if numeros: return int(numeros[0])
    except: pass
    return 0

def obtener_metadatos(nombre_limpio):
    """Busca carátula y duración en la API de Cinemeta."""
    datos = {"poster": "stremio_logo", "runtime": 0}
    if nombre_limpio == "Stremio": return datos
    
    try:
        query = urllib.parse.quote(nombre_limpio)
        # 1. Intentar como Serie
        url_series = f"https://v3-cinemeta.strem.io/catalog/series/top/search={query}.json"
        resp = requests.get(url_series, timeout=2)
        data = resp.json()
        
        if 'metas' in data and len(data['metas']) > 0:
            item = data['metas'][0]
            datos["poster"] = item.get('poster', 'stremio_logo')
            datos["runtime"] = extraer_minutos(item.get('runtime', 0))
            return datos
        
        # 2. Intentar como Película
        url_movie = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={query}.json"
        resp = requests.get(url_movie, timeout=2)
        data = resp.json()
        
        if 'metas' in data and len(data['metas']) > 0:
            item = data['metas'][0]
            datos["poster"] = item.get('poster', 'stremio_logo')
            datos["runtime"] = extraer_minutos(item.get('runtime', 0))
            return datos
            
    except Exception as e:
        log(f"⚠️ Error buscando metadatos: {e}")
    
    return datos