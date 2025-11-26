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

def limpiar_titulo_api(api_name, nombre_original):
    """
    Limpia títulos dobles tipo 'English: Japanese' o 'Title: Subtitle'.
    Intenta quedarse con la parte más parecida al nombre original.
    """
    if not api_name: return api_name
    
    # Si no hay separador común, devolver tal cual
    if ": " not in api_name:
        return api_name
        
    partes = api_name.split(": ")
    
    # Si el nombre original está contenido en alguna de las partes, usamos esa
    nombre_orig_lower = nombre_original.lower().strip()
    
    for parte in partes:
        if parte.lower().strip() in nombre_orig_lower or nombre_orig_lower in parte.lower().strip():
            return parte
            
    # Heurística: Si el título es muy largo (>30) y tiene partes,
    # probablemente la primera parte sea el título principal.
    if len(api_name) > 30:
        return partes[0]
        
    return api_name

# --- BÚSQUEDA API MEJORADA (V39.0) ---
def obtener_metadatos(nombre_busqueda, tipo_forzado="auto"):
    # Inicializamos con los datos locales como respaldo seguro
    datos = {"poster": "stremio_logo", "runtime": 0, "name": nombre_busqueda}
    
    if not nombre_busqueda or nombre_busqueda == "Stremio" or nombre_busqueda == "None": 
        return datos
    
    try:
        # Función interna para realizar la búsqueda
        def ejecutar_busqueda(termino):
            query = urllib.parse.quote(termino)
            
            def buscar_en(tipo_api):
                url = f"https://v3-cinemeta.strem.io/catalog/{tipo_api}/top/search={query}.json"
                try:
                    resp = requests.get(url, timeout=5)
                    data = resp.json()
                    
                    if 'metas' in data and len(data['metas']) > 0:
                        item = data['metas'][0]
                        
                        # 1. NOMBRE (Con limpieza)
                        api_name = item.get('name')
                        if api_name:
                            datos["name"] = limpiar_titulo_api(api_name, nombre_busqueda)
                        
                        # 2. POSTER
                        poster = item.get('poster')
                        if poster and "http" in poster:
                            datos["poster"] = poster
                        else:
                            datos["poster"] = "stremio_logo"
                        
                        # 3. DURACIÓN
                        datos["runtime"] = extraer_minutos(item.get('runtime', 0))
                        return True
                except: pass
                return False

            # LÓGICA DE PRIORIDAD
            if tipo_forzado == "serie":
                if buscar_en("series"): return True
                if buscar_en("movie"): return True 
            elif tipo_forzado == "peli":
                if buscar_en("movie"): return True
                if buscar_en("series"): return True
            else:
                if buscar_en("series"): return True
                if buscar_en("movie"): return True
            
            return False

        # INTENTO 1: Búsqueda exacta
        encontrado = ejecutar_busqueda(nombre_busqueda)
        
        # INTENTO 2: Smart Retry (Sin año)
        if not encontrado:
            # Buscar patrón de año al final (ej: "Pelicula 2024")
            match_anio = re.search(r'\s(19|20)\d{2}$', nombre_busqueda)
            if match_anio:
                nombre_sin_anio = nombre_busqueda[:match_anio.start()].strip()
                if len(nombre_sin_anio) > 2:
                    log(f"🔄 Reintentando sin año: {nombre_sin_anio}")
                    ejecutar_busqueda(nombre_sin_anio)

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