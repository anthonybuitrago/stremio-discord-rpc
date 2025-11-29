import time
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib.parse
import os
import sys
import subprocess
import logging
import psutil

from config_manager import PATH_LOG

def get_robust_session():
    """Retorna una sesión de requests con política de reintentos."""
    session = requests.Session()
    retry = Retry(
        total=1, # [OPTIMIZACION] 1 reintento para evitar desconexiones por micro-cortes
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

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
    # [MEJORADO] Eliminar paréntesis SOLO si no contienen un año (19xx o 20xx)
    # Esto limpia "(S01+02...)" pero mantiene "(2025)"
    nombre = re.sub(r'\((?!(?:19|20)\d{2}\)).*?\)', '', nombre)
    
    tipo_detectado = "auto" 

    # 1. BUSCAR EPISODIO (S01E01, 1x01, - 01)
    # [MEJORADO] El grupo débil ahora requiere guion o guion bajo (evita "Movie 2024" o "Audio 5.1")
    match_episodio = re.search(r'( S\d+E\d+(?: |$)| \d+x\d+(?: |$)|(?: - |_)0?(\d{1,4})(?:[ \-_\[\.]|$))', nombre, re.IGNORECASE)
    
    # 2. BUSCAR SOLO TEMPORADA (S01)
    # Eliminamos espacios extra en el regex para permitir coincidencia al final
    match_temporada = re.search(r'( S\d{1,2}(?: |$)| Season \d{1,2}(?: |$))', nombre, re.IGNORECASE)

    # 3. BUSCAR AÑO
    match_anio = re.search(r'\b(19\d{2}|20\d{2})\b', nombre)

    if match_episodio:
        tipo_detectado = "serie"
        # Usamos group(0) para obtener todo el match y limpiar desde ahí
        indice = match_episodio.start()
        nombre = nombre[:indice]
        
    elif match_temporada:
        tipo_detectado = "serie"
        indice = match_temporada.start()
        nombre = nombre[:indice]

    elif match_anio:
        tipo_detectado = "peli"
        indice = match_anio.start() # Usamos start() para cortar ANTES del año
        nombre = nombre[:indice]
    
    nombre = nombre.replace("mkv", "").replace("mp4", "").replace("avi", "")
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    nombre = nombre.strip(".-_ ()")

    # 4. LIMPIEZA EXTRA DE TEMPORADAS (2nd Season, Season 2, etc)
    # Esto es crucial porque la API falla con "Haikyu!! 2nd Season"
    nombre = re.sub(r'\b\d{1,2}(st|nd|rd|th)? Season\b', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'\bSeason \d{1,2}\b', '', nombre, flags=re.IGNORECASE)

    if len(nombre) < 2: return "Stremio", "auto"
    return nombre.strip(), tipo_detectado

def extract_episode_identifier(nombre_crudo):
    """Extrae el identificador de episodio (S01E01, 1x01) para comparar cambios reales."""
    if not nombre_crudo: return None
    
    # Mismo regex que en extraer_datos_video (Actualizado)
    match_episodio = re.search(r'( S\d+E\d+(?: |$)| \d+x\d+(?: |$)|(?: - |_)0?(\d{1,4})(?:[ \-_\[\.]|$))', str(nombre_crudo), re.IGNORECASE)
    
    if match_episodio:
        return match_episodio.group(0).strip()
    return None

def formatear_episodio(nombre_crudo):
    """
    Extrae y formatea la información del episodio para mostrar en Discord.
    Ejemplos:
    - "Serie S01E05" -> "Temporada 1 | Episodio 5"
    - "Serie 1x05"   -> "Temporada 1 | Episodio 5"
    - "Serie - 05"   -> "Episodio 5"
    """
    if not nombre_crudo: return None
    
    # 1. Formato S01E01
    match_s_e = re.search(r'S(\d+)E(\d+)', str(nombre_crudo), re.IGNORECASE)
    if match_s_e:
        temp = int(match_s_e.group(1))
        ep = int(match_s_e.group(2))
        return f"Temporada {temp} | Episodio {ep}"

    # 2. Formato 1x01
    match_x = re.search(r'(\d+)x(\d+)', str(nombre_crudo), re.IGNORECASE)
    if match_x:
        temp = int(match_x.group(1))
        ep = int(match_x.group(2))
        return f"Temporada {temp} | Episodio {ep}"

    # 3. Formato " - 01" o "Episode 01" (Sin temporada explícita)
    match_ep_only = re.search(r'(?: - |Episode |Episodio )(\d+)', str(nombre_crudo), re.IGNORECASE)
    if match_ep_only:
        ep = int(match_ep_only.group(1))
        return f"Episodio {ep}"

    return None

def formato_velocidad(bytes_sec):
    try:
        if bytes_sec > 1024 * 1024:
            return f"{bytes_sec / (1024 * 1024):.1f} MB/s"
        elif bytes_sec > 1024:
            return f"{bytes_sec / 1024:.0f} KB/s"
        else:
            return "0 KB/s"
    except: return "0 KB/s"







# --- LÓGICA AUTO-START ---
def get_startup_path():
    return os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', 'MediaRPC.lnk')

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
            logging.info("🗑️ Auto-start desactivado.")
            # Opcional: Notificar al usuario visualmente si fuera posible
        except Exception as e:
            logging.error(f"Error borrando link: {e}")
    
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
                creationflags=0x08000000 # CREATE_NO_WINDOW
            )
            logging.info("✅ Auto-start activado (Modo Silencioso).")
        except Exception as e:
            logging.error(f"Error creando link: {e}")

def set_autostart(enable: bool):
    """
    Fuerza el estado del auto-start basado en un booleano.
    Usado por la GUI para aplicar cambios.
    """
    currently_enabled = check_autostart()
    
    if enable and not currently_enabled:
        # Queremos activar y no está activado -> Llamamos a toggle (que lo creará)
        # Pasamos None, None porque toggle espera (icon, item) pero no los usa para la lógica core
        toggle_autostart(None, None)
    elif not enable and currently_enabled:
        # Queremos desactivar y está activado -> Llamamos a toggle (que lo borrará)
        toggle_autostart(None, None)


def is_process_running(process_name):
    """Verifica si un proceso está corriendo usando psutil (Más eficiente)."""
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                return True
        return False
    except Exception:
        return False

def get_stremio_window_title():
    """Obtiene el título de la ventana de Stremio."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        
        # Callback para EnumWindows
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        
        found_title = []

        def enum_windows_proc(hwnd, lParam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                
                # Buscamos ventanas que parezcan de Stremio
                # Stremio suele tener el título del video o "Stremio"
                # Pero necesitamos filtrar para no pillar otras cosas
                
                # Buscamos por nombre de proceso si es posible, pero es más complejo con ctypes puro.
                # Simplificación: Si el título contiene "Stremio" o coincide con lo que buscamos.
                # Mejor: Buscamos la ventana principal de la aplicación.
                
                # En Qt (Stremio usa Qt), la clase suele ser "Qt5QWindowIcon" o similar.
                # Pero el título cambia.
                
                # Vamos a devolver cualquier título que NO sea "Stremio" exacto pero que parezca un video?
                # No, eso es arriesgado.
                
                # Estrategia: Buscar ventana visible cuyo proceso sea Stremio.exe
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                
                # Aquí necesitaríamos psutil para verificar el nombre del proceso
                try:
                    import psutil
                    proc = psutil.Process(pid.value)
                    process_name = proc.name().lower()
                    
                    # logging.info(f"🐛 DEBUG: Window '{title}' | Process: {process_name}")
                    
                    if "stremio" in process_name:
                        # Ignorar ventanas ocultas o vacías
                        if user32.IsWindowVisible(hwnd) and title:
                            # logging.info(f"🐛 DEBUG: Stremio Window Found: '{title}'")
                            found_title.append(title)
                            return False # Stop enumeration
                except Exception as e:
                    # logging.error(f"Error checking process for window {hwnd}: {e}")
                    pass
                    
            return True # Continue enumeration

        user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
        
        if found_title:
            return found_title[0]
            
    except Exception as e:
        logging.error(f"Error obteniendo título de ventana: {e}")
        
    return None      
def check_for_updates(current_version):
    """
    Comprueba si hay una nueva versión en GitHub.
    Retorna (bool, str): (Hay actualización, Nueva versión)
    """
    try:
        url = "https://api.github.com/repos/anthonybuitrago/stremio-discord-rpc/releases/latest"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            latest_tag = data.get("tag_name", "").strip()
            
            # Limpieza básica de 'v' (v5.2 -> 5.2)
            curr = current_version.lower().lstrip('v')
            latest = latest_tag.lower().lstrip('v')
            
            if curr != latest:
                return True, latest_tag
    except Exception as e:
        logging.error(f"Error buscando actualizaciones: {e}")
    
    return False, ""
