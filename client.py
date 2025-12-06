import time
import threading
import requests
import urllib.parse
import logging
from pypresence import Presence, ActivityType
import os
import sys

import config_manager
import utils
import media_manager
import smtc_manager
import server
import trakt_manager

class StremioRPCClient:
    def __init__(self):
        self.running = True
        self.config = config_manager.cargar_config()
        self.rpc = None
        self.last_title = ""
        self.last_raw_title = ""
        self.last_update = 0
        self.start_time = None
        self.end_time = None
        self.current_poster = "stremio_logo"
        self.official_title = ""
        self.last_source = None # "stremio" or "music"
        self.current_client_id = None
        self.stremio_was_connected = False # [NUEVO] Para logs de conexión
        self.session = utils.get_robust_session() # [OPTIMIZACION] Sesión persistente (Keep-Alive)
        self.last_stream_idx = None # [NUEVO] Para detectar cambios de episodio en packs
        self.last_trakt_log_str = "" # [NUEVO] Para evitar spam de logs Trakt
        
        # [EXTENSION]
        self.extension_info = None
        server.start_server(self._on_extension_update)

    def connect_discord(self, target_id=None):
        """Conecta a Discord con el ID especificado. Si cambia el ID, reconecta."""
        if target_id is None:
            target_id = self.config["client_id"]

        # Si ya estamos conectados con el mismo ID, no hacemos nada
        if self.rpc and self.current_client_id == target_id:
            return self.rpc

        # Si hay una conexión activa con otro ID, la cerramos
        if self.rpc:
            try:
                logging.info(f"🔌 Cambiando identidad RPC (Nuevo ID: {target_id})...")
                self.rpc.close()
            except: pass
            self.rpc = None

        self.current_client_id = target_id
        
        while self.rpc is None and self.running:
            try:
                logging.info(f"Conectando a Discord (ID: {target_id})...")
                self.rpc = Presence(target_id)
                self.rpc.connect()
                logging.info(f"✅ Conectado a Discord ({'Música' if target_id == self.config.get('music_client_id') else 'Stremio'})")
            except Exception as e:
                logging.error(f"Error conectando a Discord: {e}")
                time.sleep(2)
        return self.rpc

    def _fetch_stremio_data(self):
        """Intenta obtener datos de Stremio. Retorna (connected, data, error)."""
        try:
            # Usamos la sesión persistente
            response = self.session.get("http://127.0.0.1:11470/stats.json", timeout=3)
            if response.status_code == 200:
                return True, response.json(), None
            else:
                return False, {}, f"Status {response.status_code}"
        except Exception as e:
            msg = str(e)
            if "10061" in msg or "refused" in msg:
                msg = "No se pudo conectar (Stremio cerrado)"
            elif "Max retries exceeded" in msg:
                msg = "Tiempo de espera agotado"
            return False, {}, msg

    def _process_video_stats(self, video):
        """Calcula estadísticas de descarga."""
        try:
            total = float(video.get("total", 0))
            downloaded = float(video.get("downloaded", 0))
            if total > 0:
                percentage = (downloaded / total) * 100
                return f"💾 {percentage:.0f}%"
        except:
            pass
        return None

    def _update_rpc(self, clean_name, video_type, stats_text, raw_name, stream_idx=None):
        """Actualiza la presencia de Discord si es necesario."""
        
        # [MODIFICADO] Asegurar conexión si se cerró previamente para historial
        # [MODIFICADO] La conexión ya se asegura en run_logic con el ID correcto

        current_time = time.time()

        # Si cambió el título, buscamos nuevos metadatos
        if clean_name != self.last_title:
            self.last_title = clean_name
            
            logging.info(f"🔎 API: {clean_name} ({video_type})")
            meta = media_manager.search_cinemeta(clean_name, video_type)
            
            self.current_poster = meta["poster"]
            self.official_title = meta["name"]

        # [MEJORADO] Lógica robusta para reiniciar tiempo
        # Evita reinicios falsos cuando Stremio deja de enviar el nombre del archivo (fallback)
        new_ep_id = utils.extract_episode_identifier(raw_name)
        old_ep_id = utils.extract_episode_identifier(self.last_raw_title)
        
        should_reset_timer = False
        
        # 1. Si ambos tienen ID (ej: S01E01 -> S01E02), y son distintos -> RESET
        if new_ep_id and old_ep_id and new_ep_id != old_ep_id:
            should_reset_timer = True
            
        # 2. Si veníamos de vacío (Inicio o tras Clear) -> RESET
        elif not self.last_raw_title:
            should_reset_timer = True

        # [NUEVO] 3. Si pasamos de "Sin ID" a "Con ID" (Peli -> Serie o Fallback -> Serie)
        elif new_ep_id and not old_ep_id:
             should_reset_timer = True
            
        # 4. Si no hay IDs (Peliculas), confiamos en el cambio de raw_name
        # PERO solo si no parece un fallback (es decir, si el clean_name también cambió)
        elif not new_ep_id and not old_ep_id:
            if raw_name != self.last_raw_title and clean_name != self.last_title:
                should_reset_timer = True

        # [NUEVO] 5. Si cambia el índice del stream (Para packs donde el nombre no cambia)
        elif stream_idx is not None and self.last_stream_idx is not None and stream_idx != self.last_stream_idx:
            should_reset_timer = True

        # Actualizamos siempre el raw title y stream_idx
        if raw_name != self.last_raw_title:
             self.last_raw_title = raw_name
        
        if stream_idx is not None:
            self.last_stream_idx = stream_idx

        if should_reset_timer:
            self.start_time = time.time()
            logging.info(f"⏱️ Nuevo episodio detectado ({new_ep_id if new_ep_id else 'Peli/Otro'}). Reiniciando tiempo.")

        # Actualizamos RPC cada 15 segundos
        if current_time - self.last_update > 15:
            try:
                buttons_list = None
                if self.config.get("show_search_button", True):
                    url_btn = f"https://www.google.com/search?q={urllib.parse.quote(self.official_title)}+anime"
                    buttons_list = [{"label": "Buscar Anime 🔎", "url": url_btn}]

                self.rpc.update(
                    activity_type=ActivityType.WATCHING,
                    details=self.official_title,
                    state=None, # Eliminado a petición del usuario
                    large_image=self.current_poster,
                    large_text=stats_text,
                    # small_image="stremio_logo", # Eliminado a petición
                    # small_text="Stremio",
                    start=self.start_time,
                    buttons=buttons_list
                )
                self.last_update = current_time
            except Exception as e:
                logging.error(f"Error actualizando RPC: {e}")
                self.connect_discord()

    def _clear_rpc(self):
        """Limpia la presencia."""
        try:
            # [MODIFICADO] Eliminada verificación de proceso. Si la API desconecta, limpiamos.
            # Esto corrige el bug donde la actividad persistía al cerrar Stremio.

            if self.rpc:
                if self.last_source in ["music", "extension_music"]:
                    # Para música, queremos que desaparezca INSTANTÁNEAMENTE
                    # logging.info("🧹 Limpiando actividad de música...")
                    self.rpc.clear()
                else:
                    # Para Stremio, cerramos conexión para intentar dejar "Actividad Reciente"
                    # O simplemente cerramos para ahorrar recursos
                    self.rpc.close()
                    self.rpc = None
            
            self.last_title = ""
            self.last_raw_title = ""
            # logging.info("❌ RPC Limpiado/Cerrado")

        except Exception as e:
            logging.error(f"Error limpiando RPC: {e}")


    def _get_active_file_name(self, video):
        """Intenta detectar el archivo exacto que se está reproduciendo."""
        try:
            # video = list(data.values())[-1] # REMOVED: Now receives video object directly
            files = video.get('files', [])
            selections = video.get('selections', [])
            
            if not files or not selections:
                # logging.info("🐛 DEBUG: Files or Selections empty. Returning None.")
                return None

            # 1. Calcular tamaño total y buscar índice de pieza máximo
            total_size = sum(f.get('length', 0) for f in files)
            max_piece = 0
            prio_piece = -1
            
            max_prio = 0
            for s in selections:
                if s.get('to', 0) > max_piece:
                    max_piece = s['to']
                
                # [MODIFICADO] Buscamos la pieza con mayor prioridad (>0)
                # Antes solo buscaba priority == 1, lo que podía fallar si Stremio usaba otro valor
                prio = s.get('priority', 0)
                if prio > max_prio:
                    max_prio = prio
                    prio_piece = s.get('from', 0)
            
            # logging.info(f"DEBUG: MaxPiece={max_piece}, PrioPiece={prio_piece}, MaxPrio={max_prio}")
            
            if prio_piece == -1: 
                # [MODIFICADO] Fallback para videos 100% buferados
                # Si no hay pieza prioritaria (prio=-1), usamos la primera selección.
                # Esto corrige el problema donde videos vistos (pero cargados) eran ignorados.
                if selections:
                    prio_piece = selections[0].get('from', 0)
                    # logging.info(f"🐛 DEBUG: Using fallback prio_piece={prio_piece}")
                else:
                    # logging.info("🐛 DEBUG: No active piece found and no selections")
                    return None

            if max_piece == 0: 
                # logging.info("🐛 DEBUG: Max piece is 0")
                return None

            # 2. Estimar tamaño de pieza (Upper Bound Logic)
            # El tamaño de pieza debe ser tal que piece_size * max_piece <= total_size
            est_max_piece_size = total_size / max_piece
            
            # Tamaños comunes de pieza (256KB a 16MB)
            common_sizes = [256*1024, 512*1024, 1024*1024, 2*1024*1024, 4*1024*1024, 8*1024*1024, 16*1024*1024]
            
            # Buscar el tamaño más grande que sea válido
            piece_size = common_sizes[0]
            for size in common_sizes:
                if size <= est_max_piece_size:
                    piece_size = size
                else:
                    break
            
            # 3. Calcular offset y buscar archivo
            current_offset = prio_piece * piece_size
            
            # logging.info(f"🐛 DEBUG: Offset={current_offset}, PieceSize={piece_size}")

            for f in files:
                start = f.get('offset', 0)
                length = f.get('length', 0)
                if start <= current_offset < (start + length):
                    # logging.info(f"🐛 DEBUG: File Found: {f.get('name')}")
                    return f.get('name')
            
            # logging.info("🐛 DEBUG: No file matched the offset.")
                    
        except Exception as e:
            logging.error(f"Error detectando archivo: {e}")
            
        return None

    def _select_best_video(self, data):
        """Selecciona el mejor candidato de video basado en actividad."""
        best_candidate = None
        best_score = -1
        
        # logging.info(f"🐛 DEBUG: Evaluating {len(data)} candidates...")

        for key, video in data.items():
            score = 0
            
            # 1. Check if it has an active file (Strongest signal)
            # Si tiene un archivo activo (selections), es casi seguro lo que el usuario ve.
            active_file = self._get_active_file_name(video)
            if active_file:
                score += 1000
                
            # 2. Check download speed
            speed = float(video.get('downloadSpeed', 0))
            if speed > 1000: # > 1KB/s
                score += 100
            elif speed > 0:
                score += 50
                
            # 3. Check connections
            peers = int(video.get('swarmConnections', 0))
            if peers > 0:
                score += 10
                
            # 4. Recency (slight preference for later items in the list)
            score += 1
            
            # logging.info(f"🐛 Candidate: {video.get('name', 'Unknown')[:30]}... | Score: {score} | ActiveFile: {active_file}")
            
            if score > best_score:
                best_score = score
                best_candidate = video
        
        return best_candidate

    def _on_extension_update(self, data):
        """Callback cuando la extensión envía datos."""
        self.extension_info = {
            "data": data,
            "timestamp": time.time()
        }

    def _handle_extension_rpc(self):
        """Maneja datos provenientes de la extensión (Prioridad Máxima)."""
        if not self.extension_info:
            return False
            
        # Verificar si los datos son recientes (10 segundos de validez)
        if time.time() - self.extension_info["timestamp"] > 10:
            return False
            
        data = self.extension_info["data"]
        
        if not data.get("is_playing"):
            return False

        # 1. YouTube Music
        if data["source"] == "youtube_music":
            if not self.config.get("enable_music_rpc", True):
                return False

            target_id = self.config.get("music_client_id") or self.config["client_id"]
            self.connect_discord(target_id)
            
            # Evitar spam
            if (self.last_source == "extension_music" and 
                self.last_media_name == data['title'] and
                self.last_artist == data['artist']):
                return True

            self.last_source = "extension_music"
            self.last_media_name = data['title']
            self.last_artist = data['artist']
            
            logging.info(f"🌐 Extensión (Music): {data['title']} - {data['artist']}")
            
            # Botón para abrir canción
            buttons = []
            if data.get("url"):
                buttons.append({"label": "Escuchar en YouTube 🎵", "url": data["url"]})

            self.rpc.update(
                activity_type=ActivityType.LISTENING,
                details=data['title'],
                state=data['artist'],
                large_image=data['cover'] if data['cover'] else "music_icon",
                buttons=buttons if buttons else None
            )
            return True

        # 2. Stremio Web
        elif data["source"] == "stremio_web":
            target_id = self.config["client_id"]
            self.connect_discord(target_id)
            
            # Limpieza básica del título
            raw_title = data['title']
            clean_name, video_type = utils.extraer_datos_video(raw_title)
            
            # Intentar buscar metadatos reales
            if clean_name != self.last_title:
                self.last_title = clean_name
                logging.info(f"🌐 Extensión (Stremio): {clean_name}")
                meta = media_manager.search_cinemeta(clean_name, video_type)
                self.current_poster = meta["poster"]
                self.official_title = meta["name"]
            
            # Actualizar RPC
            # Usamos lógica simplificada para Stremio Web por ahora
            if time.time() - self.last_update > 15:
                self.rpc.update(
                    activity_type=ActivityType.WATCHING,
                    details=self.official_title,
                    state=None,
                    large_image=self.current_poster,
                    start=self.start_time if self.start_time else time.time()
                )
                self.last_update = time.time()
            
            self.last_source = "extension_stremio"
            return True

        return False

    def _handle_music_rpc(self):
        """Maneja la lógica de detección y RPC de música."""
        if not self.config.get("enable_music_rpc", True):
            return False

        music_info = smtc_manager.get_media_info()
        
        if music_info and music_info.get("is_playing"):
            target_id = self.config.get("music_client_id")
            if not target_id: target_id = self.config["client_id"]
            
            self.connect_discord(target_id)
            
            # Evitar spam de actualizaciones si es la misma canción
            if (self.last_source == "music" and 
                self.last_media_name == music_info['title'] and
                self.last_artist == music_info['artist']):
                return True

            # Buscar carátula
            search_query = f"{music_info['artist']} {music_info['title']}"
            meta = media_manager.search_metadata(search_query)
            cover_url = meta['cover_url'] if meta else None

            # Actualizar RPC
            self.last_source = "music"
            self.last_media_name = music_info['title']
            self.last_artist = music_info['artist']
            
            logging.info(f"🎵 Música detectada: {music_info['title']} - {music_info['artist']}")

            large_img = cover_url if cover_url else "music_icon"
            
            self.rpc.update(
                activity_type=ActivityType.LISTENING,
                details=music_info['title'],
                state=music_info['artist'],
                large_image=large_img,
                # small_image="music_icon", # Eliminado a petición
                # small_text="YouTube Music"
            )
            return True
            
        return False

    def _handle_stremio_rpc(self):
        """Maneja la lógica de detección y RPC de Stremio."""
        # A. Intentar leer Stremio
        connected, data, error_msg = self._fetch_stremio_data()
        
        # Log de estado de conexión
        if connected and not self.stremio_was_connected:
            logging.info("✅ Stremio detectado (API conectada)")
            self.stremio_was_connected = True
        elif not connected and self.stremio_was_connected:
            logging.info(f"❌ Stremio cerrado o API desconectada. Razón: {error_msg}")
            self.stremio_was_connected = False

        if connected and len(data) > 0:
            # Selección inteligente de candidato
            video = self._select_best_video(data)
            
            if video:
                # [TRAKT INTEGRATION]
                # Si tenemos credenciales, preguntamos a Trakt primero
                trakt_conf = self.config.get("trakt")
                if trakt_conf and trakt_conf.get("username") and trakt_conf.get("client_id"):
                    try:
                        trakt_info = trakt_manager.get_user_activity(
                            trakt_conf["username"], 
                            trakt_conf["client_id"]
                        )
                        
                        if trakt_info:
                            # Log solo si cambia la info
                            current_log_str = f"{trakt_info['title']} - {trakt_info.get('details', '')}"
                            if current_log_str != self.last_trakt_log_str:
                                logging.info(f"🕵️ Trakt: {current_log_str} ({trakt_info['action']})")
                                self.last_trakt_log_str = current_log_str
                            
                            # Conectar a Discord
                            self.connect_discord(self.config["client_id"])
                            
                            # Actualizar RPC con datos de Trakt
                            self.last_source = "trakt"
                            
                            # Buscar poster usando IMDB ID si es posible
                            poster = "stremio_logo"
                            if trakt_info.get("imdb_id"):
                                # Usamos Cinemeta para buscar el poster oficial con el ID
                                # Esto es más seguro que buscar por nombre
                                meta = media_manager.search_cinemeta(trakt_info["imdb_id"], "auto")
                                poster = meta["poster"]
                            
                            self.rpc.update(
                                activity_type=ActivityType.WATCHING,
                                details=trakt_info['title'],
                                state=trakt_info.get('details'), # S01E01 - Title
                                large_image=poster,
                                # small_image="trakt_icon", # Opcional
                                # small_text="Trakt.tv"
                            )
                            return True
                    except Exception as e:
                        logging.error(f"Error Trakt: {e}")

                # [FALLBACK] Lógica original (Adivinar por nombre de archivo)
                # Intentar detectar el archivo específico (Episodio)
                active_file = self._get_active_file_name(video)
                
                if active_file:
                    raw_name = active_file
                elif video.get('name'):
                    raw_name = str(video.get('name'))
                else:
                    raw_name = ""
            else:
                    # Si no hay candidato válido (solo seeding), usar título de ventana
                    window_title = utils.get_stremio_window_title()
                    if window_title:
                        logging.info(f"ℹ️ Fallback: Usando título de ventana: {window_title}")
                        raw_name = window_title
                    else:
                        raw_name = ""
            
            if raw_name:
                clean_name, video_type = utils.extraer_datos_video(raw_name)
                if clean_name:
                    stats_text = self._process_video_stats(video)
                    
                    # PRIORIDAD 1: STREMIO (Si no hay música)
                    self.connect_discord(self.config["client_id"])
                    
                    # Extraer streamIdx si existe
                    stream_idx = video.get("streamIdx")
                    
                    self._update_rpc(clean_name, video_type, stats_text, raw_name, stream_idx)
                    self.last_source = "stremio"
                    return True
        
        # [DEBUG] Log si estamos conectados pero no hay datos (o no hay video válido)
        if connected and len(data) == 0:
             # Solo loguear una vez para no spammear
             if self.last_source == "stremio":
                 logging.info("ℹ️ Stremio conectado pero sin datos de reproducción (Menú/Pausa).")
        
        return False

    def _cleanup_rpc(self):
        """Limpia o cierra la conexión RPC si no hay actividad."""
        # Limpiamos si hay alguna fuente activa previa
        if self.last_source:
            self._clear_rpc()
            self.last_source = None

    def run_logic(self):
        logging.info(f"🚀 Media RPC {config_manager.APP_VERSION} Iniciado")
        # [OPTIMIZACION] No conectamos al inicio por defecto.

        while self.running:
            # 1. Recargar Configuración Dinámica
            self.config = config_manager.cargar_config()

            # 2. Chequear Flag de Reinicio
            flag_path = os.path.join(os.path.dirname(config_manager.PATH_CONFIG), "rpc_restart.flag")
            if os.path.exists(flag_path):
                logging.info("♻️ Reiniciando RPC a petición del usuario...")
                try:
                    if self.rpc: 
                        self.rpc.close()
                        self.rpc = None
                    os.remove(flag_path)
                except: pass

            try:

                # [MODIFICADO] PRIORIDAD: EXTENSIÓN > MÚSICA > STREMIO
                extension_active = self._handle_extension_rpc()
                
                # Check if extension is connected (alive recently)
                # If extension is connected but NOT active (Paused), we MUST skip music_rpc
                # to avoid falling back to SMTC which might incorrectly report "Playing".
                is_ext_active_or_connected = False
                if self.extension_info and (time.time() - self.extension_info["timestamp"] < 10):
                    is_ext_active_or_connected = True

                music_active = False
                # Solo chequeamos SMTC si la extensión NO está presente ni activa
                if not extension_active and not is_ext_active_or_connected:
                    music_active = self._handle_music_rpc()
                
                stremio_active = False
                if not extension_active and not music_active:
                    stremio_active = self._handle_stremio_rpc()
                
                # C. Limpieza
                if not extension_active and not music_active and not stremio_active:
                    self._cleanup_rpc()

            except Exception as e:
                logging.error(f"Error Loop: {e}")
                time.sleep(self.config["update_interval"])
            
            time.sleep(self.config["update_interval"])

        try: 
            if self.rpc: self.rpc.close() 
        except Exception: pass

    def stop(self):
        self.running = False
