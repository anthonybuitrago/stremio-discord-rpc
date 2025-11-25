import time
import re
import requests
import urllib.parse
import os
import sys
import subprocess
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
    try:
        if os.path.exists(PATH_LOG) and os.path.getsize(PATH_LOG) > 1 * 1024 * 1024:
            with open(PATH_LOG, "w", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] 🧹 Log limpiado automáticamente.\n")
    except: pass

# --- LIMPIEZA DE NOMBRE (SMART CUT) ---
def extraer_datos_video(nombre_crudo):
    if not nombre_crudo or str(nombre_crudo).lower() == "none":
        return None, "auto"

    nombre = nombre_crudo.replace(".", " ")
    nombre = re.sub(r'\[.*?\]', '', nombre)
    nombre = re.sub(r'\(.*?\)', '', nombre)
    
    tipo_detectado = "auto" 

    # 1. BUSCAR EPISODIO (S01E01, 1x01, - 01)
    match_episodio = re.search(r'( S\d+E\d+ | \d+x\d+ | [ \-_]0?(\d{1,4})(?:[ \-_\[\.]) )', nombre, re.IGNORECASE)
    
    # 2. BUSCAR SOLO TEMPORADA (S01)
    match_temporada = re.search(r'( S\d{1,2} | Season \d{1,2} )', nombre, re.IGNORECASE)

    # 3. BUSCAR AÑO
    match_anio = re.search(r'\b(19\d{2}|20\d{2})\b', nombre)

    if match_episodio:
        tipo_detectado = "serie"
        indice = match_episodio.start()
        nombre = nombre[:indice]
        
    elif match_temporada:
        tipo_detectado = "serie"
        indice = match_temporada.start()
        nombre = nombre[:indice]

    elif match_anio:
        tipo_detectado = "peli"
        indice = match_anio.end()
        nombre = nombre[:indice]
    
    nombre = nombre.replace("mkv", "").replace("mp4", "").replace("avi", "")
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    nombre = nombre.strip(".-_ ")

    if len(nombre) < 2: return "Stremio", "auto"
    return nombre, tipo_detectado

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

# --- BÚSQUEDA API MEJORADA (V39.0) ---
def obtener_metadatos(nombre_busqueda, tipo_forzado="auto"):
    # Inicializamos con los datos locales como respaldo seguro
    datos = {"poster": "stremio_logo", "runtime": 0, "name": nombre_busqueda}
    
    if not nombre_busqueda or nombre_busqueda == "Stremio" or nombre_busqueda == "None": 
        return datos
    
    try:
        query = urllib.parse.quote(nombre_busqueda)
        
        def buscar_en(tipo_api):
            url = f"https://v3-cinemeta.strem.io/catalog/{tipo_api}/top/search={query}.json"
            resp = requests.get(url, timeout=2)
            data = resp.json()
            
            if 'metas' in data and len(data['metas']) > 0:
                item = data['metas'][0]
                
                # 1. CONTROL DE CALIDAD: NOMBRE
                # Si la API devuelve nombre vacío, mantenemos el nuestro
                api_name = item.get('name')
                if api_name:
                    datos["name"] = api_name
                
                # 2. CONTROL DE CALIDAD: POSTER
                # Si el poster está roto, usamos el logo
                poster = item.get('poster')
                if poster and "http" in poster:
                    datos["poster"] = poster
                else:
                    datos["poster"] = "stremio_logo"
                
                # 3. DURACIÓN
                datos["runtime"] = extraer_minutos(item.get('runtime', 0))
                return True
            return False

        # LÓGICA DE PRIORIDAD MODIFICADA
        if tipo_forzado == "serie":
            if buscar_en("series"): return datos
            if buscar_en("movie"): return datos 
            
        elif tipo_forzado == "peli":
            if buscar_en("movie"): return datos
            if buscar_en("series"): return datos
            
        else:
            # MODO AUTO: CAMBIO IMPORTANTE AQUÍ
            # Antes buscábamos peli primero. AHORA SERIE PRIMERO.
            # Esto arregla Haikyuu!!
            if buscar_en("series"): return datos
            if buscar_en("movie"): return datos

    except Exception as e:
        log(f"⚠️ Error Metadata: {e}")
    
    return datos

# --- LÓGICA AUTO-START ---
def get_startup_path():
    return os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', 'StremioRPC.lnk')

def check_autostart():
    return os.path.exists(get_startup_path())

def toggle_autostart(icon, item):
    """
    [MODIFICADO] Crea o elimina el acceso directo.
    Ahora soporta pythonw.exe para evitar ventanas negras en modo desarrollo.
    """
    link_path = get_startup_path()
    
    # Lógica para definir Target y Argumentos
    arguments = "" # Por defecto vacío
    
    if getattr(sys, 'frozen', False):
        # MODO EXE: El target es el propio ejecutable
        target = sys.executable
        work_dir = os.path.dirname(target)
    else:
        # MODO SCRIPT: Usamos pythonw.exe y pasamos el script como argumento
        current_python_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(current_python_dir, 'pythonw.exe')
        
        target = pythonw
        # Comillas para evitar errores con espacios en rutas
        script_path = os.path.abspath(sys.argv[0])
        arguments = f'"{script_path}"'
        work_dir = os.path.dirname(script_path)

    # Si ya existe, lo borramos (Toggle OFF)
    if os.path.exists(link_path):
        try:
            os.remove(link_path)
            log("🗑️ Auto-start desactivado.")
            # Opcional: Notificar al usuario visualmente si fuera posible
        except Exception as e:
            log(f"Error borrando link: {e}")
    
    # Si no existe, lo creamos (Toggle ON)
    else:
        try:
            # [MODIFICADO] Script PowerShell ahora incluye .Arguments y .WindowStyle
            ps_script = f"""
            $ws = New-Object -ComObject WScript.Shell;
            $s = $ws.CreateShortcut('{link_path}');
            $s.TargetPath = '{target}';
            $s.Arguments = '{arguments}';
            $s.WorkingDirectory = '{work_dir}';
            $s.WindowStyle = 7;
            $s.Save()
            """
            # WindowStyle 7 = Minimizada (por seguridad)
            
            subprocess.run(
                ["powershell", "-Command", ps_script], 
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            log("✅ Auto-start activado (Modo Silencioso).")
        except Exception as e:
            log(f"Error creando link: {e}")