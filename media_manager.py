import ctypes
import logging
import re
import requests
import urllib.parse
import utils # Import utils for get_robust_session

# Cache para guardar metadatos completos
# Key: Query string -> Value: Dict {cover, artist, title, album}
METADATA_CACHE = {}
CINEMETA_CACHE = {}

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

def search_cinemeta(nombre_busqueda, tipo_forzado="auto"):
    """Busca metadatos en Cinemeta (Stremio)."""
    # Verificar cache
    cache_key = (nombre_busqueda, tipo_forzado)
    if cache_key in CINEMETA_CACHE:
        return CINEMETA_CACHE[cache_key]

    # Inicializamos con los datos locales como respaldo seguro
    datos = {"poster": "stremio_logo", "runtime": 0, "name": nombre_busqueda}
    
    if not nombre_busqueda or nombre_busqueda == "Stremio" or nombre_busqueda == "None": 
        return datos
    
    try:
        # Usamos una sesión robusta para evitar fallos por red inestable
        session = utils.get_robust_session()

        # Función interna para realizar la búsqueda
        def ejecutar_busqueda(termino):
            query = urllib.parse.quote(termino)
            
            def buscar_en(tipo_api):
                url = f"https://v3-cinemeta.strem.io/catalog/{tipo_api}/top/search={query}.json"
                try:
                    resp = session.get(url, timeout=5)
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
                    logging.info(f"🔄 Retrying without year: {nombre_sin_anio}")
                    ejecutar_busqueda(nombre_sin_anio)

    except Exception as e:
        logging.error(f"⚠️ Error Metadata: {e}")
    # Guardar en cache
    CINEMETA_CACHE[cache_key] = datos
    return datos

def _process_itunes_result(item):
    # Obtener imagen de alta resolución
    artwork = item.get("artworkUrl100")
    if artwork:
        artwork = artwork.replace("100x100bb", "600x600bb")
    
    return {
        "cover_url": artwork,
        "artist": item.get("artistName"),
        "title": item.get("trackName"),
        "album": item.get("collectionName")
    }

def search_metadata(query):
    """
    Busca en iTunes API y retorna metadatos completos (Cover, Artista, Canción, Álbum).
    """
    if not query: return None
    
    # Limpieza básica del query
    query = re.sub(r'[\(\[].*?[\)\]]', '', query) # Quitar (Official Video), [Lyrics], etc.
    query = query.strip()
    
    if query in METADATA_CACHE:
        return METADATA_CACHE[query]
        
    try:
        # Intentar búsqueda principal (US por defecto)
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&media=music&entity=song&limit=1"
        resp = requests.get(url, timeout=2)
        
        if resp.status_code == 200:
            data = resp.json()
            if data["resultCount"] > 0:
                result = _process_itunes_result(data["results"][0])
                METADATA_CACHE[query] = result
                return result
        
        # [NUEVO] Fallback: Intentar en tienda de México (MX) para música latina
        url_mx = f"{url}&country=MX"
        resp = requests.get(url_mx, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if data["resultCount"] > 0:
                result = _process_itunes_result(data["results"][0])
                METADATA_CACHE[query] = result
                return result

        # [NUEVO] Fallback: Intentar en tienda de Japón (JP) para música asiática/anime
        url_jp = f"{url}&country=JP"
        resp = requests.get(url_jp, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if data["resultCount"] > 0:
                result = _process_itunes_result(data["results"][0])
                METADATA_CACHE[query] = result
                return result

        # [NUEVO] Fallback Final: Deezer API (Excelente para música internacional/indie)
        url_deezer = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}"
        resp = requests.get(url_deezer, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                item = data["data"][0]
                result = {
                    "cover_url": item["album"]["cover_xl"],
                    "artist": item["artist"]["name"],
                    "title": item["title"],
                    "album": item["album"]["title"]
                }
                METADATA_CACHE[query] = result
                return result

    except Exception as e:
        logging.error(f"Error buscando metadatos: {e}")
    
    return None

def get_media_info():
    try:
        titles = _get_window_titles()
        for title in titles:
            lower_title = title.lower()
            
            # 1. YouTube (Browser)
            if "youtube" in lower_title:
                clean_title = _clean_browser_title(title)
                if clean_title:
                    # Ignorar títulos genéricos
                    if clean_title.lower() in ["youtube", "youtube music", "reproduciendo"]:
                        continue

                    # Intentamos separar, pero confiamos más en la búsqueda de internet
                    parts = clean_title.split(" - ")
                    
                    search_query = clean_title
                    local_artist = None
                    local_song = clean_title
                    
                    # [MODIFICADO] Lógica Conservadora
                    # Si NO hay guión, asumimos que falta el artista en la ventana.
                    # En este caso, NO buscamos en internet para evitar falsos positivos.
                    if len(parts) < 2:
                        return {
                            "title": local_song,
                            "artist": None,
                            "album_title": "YouTube Music",
                            "is_playing": True,
                            "cover_url": None
                        }
                    
                    # Si hay guión, procedemos normal
                    local_artist = parts[0]
                    local_song = parts[1]
                    search_query = f"{local_artist} {local_song}"
                    
                    # BUSCAR EN INTERNET (iTunes)
                    meta = search_metadata(search_query)
                    
                    # VALIDACIÓN DE SEGURIDAD
                    # Si tenemos un artista local y el de iTunes es totalmente diferente, descartamos iTunes.
                    # Esto evita que "Come With Me" de "Surfaces" salga como "Sammie".
                    if meta and local_artist:
                        itunes_artist = meta["artist"].lower()
                        local_artist_clean = local_artist.lower()
                        
                        # Chequeo simple: ¿Alguna palabra del artista local está en el de iTunes o viceversa?
                        # Dividimos por espacios y &
                        local_parts = re.split(r'[\s&]+', local_artist_clean)
                        match_found = False
                        for part in local_parts:
                            if len(part) > 2 and part in itunes_artist:
                                match_found = True
                                break
                        
                        # También al revés (si iTunes es "Surfaces", y local es "Surfaces & ...")
                        if not match_found and itunes_artist in local_artist_clean:
                            match_found = True
                            
                        if not match_found:
                            # logging.info(f"⚠️ Discarding false match: Local='{local_artist}' vs iTunes='{meta['artist']}'")
                            meta = None

                    if meta:
                        # Si encontramos datos oficiales y pasaron la validación
                        return {
                            "title": meta["title"],
                            "artist": meta["artist"],
                            "album_title": meta["album"] or "YouTube Music",
                            "is_playing": True,
                            "cover_url": meta["cover_url"]
                        }
                    else:
                        # Fallback: Usar lo que sacamos del título de la ventana
                        return {
                            "title": local_song,
                            "artist": local_artist, # Puede ser None
                            "album_title": "YouTube Music",
                            "is_playing": True,
                            "cover_url": None
                        }
            
            # 2. Spotify
            if "spotify" in lower_title:
                 if title.strip().lower() in ["spotify", "spotify free", "spotify premium"]:
                     continue
                 
                 parts = title.split(" - ")
                 artist = "Spotify"
                 song = title
                 if len(parts) >= 2:
                     artist = parts[0]
                     song = parts[1]
                 
                 # Buscar metadatos reales también para Spotify (para tener cover y album)
                 meta = search_metadata(f"{artist} {song}")
                 
                 if meta:
                     return {
                         "title": meta["title"],
                         "artist": meta["artist"],
                         "album_title": meta["album"] or "Spotify",
                         "is_playing": True,
                         "cover_url": meta["cover_url"]
                     }
                 else:
                     return {
                         "title": song,
                         "artist": artist,
                         "album_title": "Spotify",
                         "is_playing": True,
                         "cover_url": None
                     }

        return None
    except Exception as e:
        logging.error(f"Error getting window titles: {e}")
        return None

def _get_window_titles():
    user32 = ctypes.windll.user32
    titles = []

    def foreach_window(hwnd, lParam):
        if not user32.IsWindowVisible(hwnd): return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0: return True
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        if title: titles.append(title)
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(EnumWindowsProc(foreach_window), 0)
    return titles

def _clean_browser_title(title):
    # 1. Quitar sufijos de navegador
    title = re.sub(r' - (Personal - )?Microsoft Edge.*$', '', title)
    title = re.sub(r' - Google Chrome.*$', '', title)
    title = re.sub(r' - Mozilla Firefox.*$', '', title)
    title = re.sub(r' - Opera.*$', '', title)
    title = re.sub(r' - Brave.*$', '', title)
    title = re.sub(r' - YouTube.*$', '', title)
    # [NUEVO] Quitar prefijo "YouTube Music - " que a veces pone la PWA
    title = re.sub(r'^YouTube Music - ', '', title, flags=re.IGNORECASE)
    
    # 2. Quitar prefijos de notificaciones
    title = re.sub(r'^\(\d+\)\s*', '', title)
    
    # 3. Limpieza Avanzada de "Basura" de YouTube
    # Quitar (Official Video), [Official Audio], (Lyrics), (4K), etc.
    # Usamos IGNORECASE para que detecte mayúsculas y minúsculas
    flags = re.IGNORECASE
    title = re.sub(r'\s*[\(\[]\s*Of+icial\s*(Video|Audio|Music Video).*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*Video\s*Of+icial.*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*Lyrics.*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*Letra.*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*HQ.*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*HD.*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*4K.*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*Live.*?[\)\]]', '', title, flags=flags)
    title = re.sub(r'\s*[\(\[]\s*En Vivo.*?[\)\]]', '', title, flags=flags)
    
    # Quitar "ft.", "feat." para que busque solo el artista principal (mejora resultados)
    title = re.sub(r'\s(ft\.|feat\.|featuring)\s.*$', '', title, flags=flags)
    
    return title.strip()
