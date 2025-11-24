import time
import re
import requests
import urllib.parse
import os
import sys
import subprocess
from config_manager import PATH_LOG

def log(mensaje):
    """Escribe en el archivo de log y en consola"""
    texto = f"[{time.strftime('%H:%M:%S')}] {mensaje}"
    try:
        print(texto)
        with open(PATH_LOG, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except: pass

def gestionar_logs():
    """Limpia el archivo de log si es muy grande"""
    try:
        if os.path.exists(PATH_LOG) and os.path.getsize(PATH_LOG) > 1 * 1024 * 1024:
            with open(PATH_LOG, "w", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] 🧹 Log limpiado automáticamente.\n")
    except: pass

def limpiar_nombre(nombre_crudo, lista_negra):
    nombre = nombre_crudo.replace(".", " ")
    nombre = re.sub(r'\[.*?\]', '', nombre)
    nombre = re.sub(r'\(.*?\)', '', nombre)
    
    for basura in lista_negra:
        nombre = re.sub(r'\b' + re.escape(basura) + r'\b', '', nombre, flags=re.IGNORECASE)
        nombre = re.sub(basura, '', nombre, flags=re.IGNORECASE)
    
    nombre = nombre.replace("mkv", "").replace("mp4", "").replace("avi", "")
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    nombre = nombre.strip(".-_ ")

    if not nombre: return "Stremio"
    return nombre

def formato_velocidad(bytes_sec):
    try:
        if bytes_sec > 1024 * 1024:
            return f"{bytes_sec / (1024 * 1024):.1f} MB/s"
        elif bytes_sec > 1024:
            return f"{bytes_sec / 1024:.0f} KB/s"
        else:
            return "0 KB/s"
    except: return "0 KB/s"

def extraer_minutos(texto_runtime):
    try:
        numeros = re.findall(r'\d+', str(texto_runtime))
        if numeros: return int(numeros[0])
    except: pass
    return 0

def obtener_metadatos(nombre_limpio):
    datos = {"poster": "stremio_logo", "runtime": 0}
    if nombre_limpio == "Stremio": return datos
    
    try:
        query = urllib.parse.quote(nombre_limpio)
        url_series = f"https://v3-cinemeta.strem.io/catalog/series/top/search={query}.json"
        resp = requests.get(url_series, timeout=2)
        data = resp.json()
        if 'metas' in data and len(data['metas']) > 0:
            item = data['metas'][0]
            datos["poster"] = item.get('poster', 'stremio_logo')
            datos["runtime"] = extraer_minutos(item.get('runtime', 0))
            return datos
        
        url_movie = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={query}.json"
        resp = requests.get(url_movie, timeout=2)
        data = resp.json()
        if 'metas' in data and len(data['metas']) > 0:
            item = data['metas'][0]
            datos["poster"] = item.get('poster', 'stremio_logo')
            datos["runtime"] = extraer_minutos(item.get('runtime', 0))
            return datos
    except Exception as e:
        log(f"⚠️ Error Metadata: {e}")
    
    return datos

# --- LÓGICA AUTO-START (NUEVO) ---
def get_startup_path():
    """Devuelve la ruta de la carpeta Inicio de Windows"""
    return os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', 'StremioRPC.lnk')

def check_autostart():
    """Devuelve True si el acceso directo ya existe"""
    return os.path.exists(get_startup_path())

def toggle_autostart(icon, item):
    """Crea o borra el acceso directo usando PowerShell"""
    link_path = get_startup_path()
    
    # Detectamos qué archivo estamos ejecutando (.py o .exe)
    if getattr(sys, 'frozen', False):
        target = sys.executable # El .exe
    else:
        target = os.path.abspath(sys.argv[0]) # El .py
        
    work_dir = os.path.dirname(target)

    if os.path.exists(link_path):
        try:
            os.remove(link_path)
            log("🗑️ Auto-start desactivado (Acceso directo borrado).")
        except Exception as e:
            log(f"Error borrando link: {e}")
    else:
        try:
            # Script de PowerShell para crear acceso directo sin librerías extra
            ps_script = f"$s=(New-Object -COM WScript.Shell).CreateShortcut('{link_path}');$s.TargetPath='{target}';$s.WorkingDirectory='{work_dir}';$s.Save()"
            subprocess.run(["powershell", "-Command", ps_script], creationflags=0x08000000) # NO_WINDOW flag
            log("✅ Auto-start activado (Acceso directo creado).")
        except Exception as e:
            log(f"Error creando link: {e}")