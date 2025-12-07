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
# import trakt_manager # Removed as it was only for Stremio

class MediaRPCClient:
    def __init__(self):
        self.running = True
        self.config = config_manager.cargar_config()
        self.rpc = None
        self.last_title = ""
        self.last_update = 0
        self.start_time = None
        self.current_poster = "stremio_logo"
        self.official_title = ""
        self.last_source = None # "extension" or "music"
        self.current_client_id = None
        
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
                logging.info(f"🔌 Switching RPC Identity (New ID: {target_id})...")
                self.rpc.close()
            except: pass
            self.rpc = None

        self.current_client_id = target_id
        
        while self.rpc is None and self.running:
            try:
                # logging.info(f"Conectando a Discord (ID: {target_id})...")
                self.rpc = Presence(target_id)
                self.rpc.connect()
                logging.info(f"✅ Connected to Discord ({'Music' if target_id == self.config.get('music_client_id') else 'Media'})")
            except Exception as e:
                logging.error(f"Error conectando a Discord: {e}")
                time.sleep(2)
        return self.rpc

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
        
        # DEBUG: Log payload
        # logging.info(f"DEBUG Payload: {data}")

        if not data.get("is_playing") and data.get("type") != "ping" and data["source"] not in ["hianime", "youtube_music"]:
             return False

        # 1. YouTube Music
        if data["source"] == "youtube_music":
            # Strict check for music
            if not data.get("is_playing"):
                # Silent reset of state so resume works
                if self.last_source == "extension_music":
                     self.last_source = None
                     self.last_media_name = None
                     self.last_artist = None
                     try: self.rpc.clear()
                     except: pass
                return False

            if not self.config.get("enable_music_rpc", True):
                return False

            target_id = self.config.get("music_client_id") or self.config["client_id"]
            self.connect_discord(target_id)
            
            # Evitar spam (Content check only)
            if (getattr(self, "last_media_name", "") == data['title'] and
                getattr(self, "last_artist", "") == data['artist']):
                # Update source to track we are now on extension
                self.last_source = "extension_music"
                return True

            self.last_source = "extension_music"
            self.last_media_name = data['title']
            self.last_artist = data['artist']
            
            logging.info(f"🌐 Extension (Music): {data['title']} - {data['artist']}")
            
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

        # 2. HiAnime
        elif data["source"] == "hianime":
            target_id = self.config["client_id"] 
            self.connect_discord(target_id)
            
            # --- MANEJO DE ESTADO HÍBRIDO ---
            if not hasattr(self, "hianime_cache"):
                self.hianime_cache = {"title": None, "episode": None, "poster": None, "official_title": None}

            # A. METADATOS (Main Frame)
            if data.get("type") in ["meta", "mixed"] and data.get("title"):
                # Si cambió el título O el episodio
                new_ep = data.get("episode", "Episode 1")
                
                # Check cache init
                if self.hianime_cache["title"] != data["title"] or self.hianime_cache["episode"] != new_ep:
                    logging.info(f"🌐 Extension (HiAnime Meta): {data['title']} - {new_ep}")
                    
                    # Reset Session Start Time for accurate "Elapsed" timer
                    self.hianime_session_start = time.time()
                    
                    # Si cambió el ANIME (Título), buscamos póster nuevo
                    if data["title"] != self.hianime_cache["title"]:
                        if data.get("poster"):
                            self.hianime_cache["poster"] = data["poster"]
                            self.hianime_cache["official_title"] = data["title"] 
                        else:
                            meta = media_manager.search_cinemeta(data["title"], "series")
                            self.hianime_cache["poster"] = meta["poster"]
                            self.hianime_cache["official_title"] = meta["name"]
                    
                    # Actualizamos caché
                    self.hianime_cache["title"] = data["title"]
                    self.hianime_cache["episode"] = new_ep
                    if data.get("poster") and data["poster"] != self.hianime_cache["poster"]:
                         self.hianime_cache["poster"] = data["poster"]

            # B. ACTUALIZACIÓN RPC (Play/Meta/Mixed)
            is_playing = data.get("is_playing", False)
            msg_type = data.get("type", "unknown")
            is_hidden = data.get("is_hidden", False)
            
            # [DEBUG] Log para entender qué llega
            # logging.info(f"🔍 Packet: Type={msg_type} | Playing={is_playing} | Hidden={is_hidden} | Title={data.get('title')}")

            # [MODIFICADO] Lógica de Limpieza Super-Estricta
            # Si la ventana está OCULTA (Minimizada/Tab fondo), mandamos limpiar SIEMPRE.
            # Esto cumple la petición del usuario: "si minimizo, pausa el tiempo".
            if is_hidden:
                 if self.last_source == "extension_hianime":
                    # logging.info("🙈 HiAnime Hidden (Global) -> Clearing RPC.")
                    try: self.rpc.clear()
                    except: pass
                    self.last_source = None 
                    self.hianime_last_data = None
                 return False

            # [MODIFICADO] Lógica de Limpieza Discriminada (Solo si NO está oculto)
            # 1. Si es paquete de PLAYBACK (Video), es la autoridad sobre Pausa.
            if msg_type == "playback":
                # Registrar que tenemos playback activo
                self.hianime_last_playback_time = time.time()
                
                if not is_playing:
                    if self.last_source == "extension_hianime":
                        logging.info("⏸️ HiAnime Paused (Playback) -> Clearing RPC.")
                        try: self.rpc.clear()
                        except: pass
                        self.last_source = None 
                        self.hianime_last_data = None
                    return False
            
            # 2. Si es META/MIXED, y NO hay señal de playing...
            elif not is_playing:
                # Comprobar si hemos tenido Playback recientemente (5s)
                last_pb = getattr(self, "hianime_last_playback_time", 0)
                if time.time() - last_pb < 5:
                    # Si el video estaba reportando hace poco, ignoramos el Meta (confiamos en el video)
                    return False
                else:
                    # Si NO hay video detectado (Fallback Mode), permitimos que Meta muestre presencia
                    pass

            # Prioritizamos el título de HiAnime porque suele incluir la Temporada (Ej: "7th Season")
            current_title = self.hianime_cache["title"] or self.hianime_cache["official_title"] or "Anime"
            current_ep = self.hianime_cache["episode"] or "Watching"
            
            # Fix: Si es una película, no mostrar "Episode 1" ni "Movie" (limpiar segunda línea)
            if "movie" in current_title.lower() and current_ep == "Episode 1":
                current_ep = None
            
            current_poster = self.hianime_cache["poster"] or "stremio_logo"

            # Calcular tiempos (solo si hay datos reales de tiempo)
            start_ts = None
            
            # Opción A: Tenemos tiempo exacto del video (Playback Mode)
            if data.get("current_time") and data.get("total_time") and is_playing:
                now = time.time()
                start_ts = now - data["current_time"]
            
            # Opción B: No tenemos video, usamos tiempo de sesión (Meta Mode)
            # Esto muestra "00:00 elapsed" que cuenta hacia arriba desde que detectamos el episodio
            elif hasattr(self, "hianime_session_start") and self.hianime_session_start:
                 start_ts = self.hianime_session_start

            small_txt = "HiAnime"
            if not is_playing and msg_type == "playback":
                small_txt = "Paused"
            
            # Deduplicación estricta para evitar parpadeos
            # Solo actualizamos si cambiaron datos visuales o si saltó mucho el tiempo (seek)
            last_ts = getattr(self, "hianime_last_ts", 0) or 0
            time_jump = abs(start_ts - last_ts) if (start_ts and last_ts) else 0

            # Preparamos los datos
            new_update_data = (current_title, current_ep, small_txt, current_poster)
            last_update_data = getattr(self, "hianime_last_data", None)

            # Si todo es igual y el tiempo no saltó (>2s de ajuste), ignoramos
            # PERO si venimos de fuente nula (recién reanudado), forzamos update
            if new_update_data == last_update_data and time_jump < 2 and self.last_source == "extension_hianime":
                    return True

            self.rpc.update(
                activity_type=ActivityType.WATCHING,
                details=current_title,
                state=current_ep,
                large_image=current_poster,
                small_text=small_txt,
                start=start_ts, 
                buttons=[{"label": "Ver en HiAnime", "url": data.get("url", "https://hianime.to")}]
            )
            self.hianime_last_data = new_update_data
            if start_ts: self.hianime_last_ts = start_ts
            self.last_update = time.time()
            
            self.last_source = "extension_hianime"
            return True
        
        return False

    def _handle_music_rpc(self):
        """Maneja la lógica de detección y RPC de música."""
        if not self.config.get("enable_music_rpc", True):
            return False

        music_info = smtc_manager.get_media_info()
        
        # 1. Si está sonando
        if music_info and music_info.get("is_playing"):
            target_id = self.config.get("music_client_id")
            if not target_id: target_id = self.config["client_id"]
            
            self.connect_discord(target_id)
            
            # Evitar spam (Checking Content only, ignoring source change to prevent flip-flop spam)
            if (getattr(self, "last_media_name", "") == music_info['title'] and
                getattr(self, "last_artist", "") == music_info['artist']):
                # Update source just in case, but don't log duplicate
                self.last_source = "music"
                return True

            # Buscar carátula
            search_query = f"{music_info['artist']} {music_info['title']}"
            meta = media_manager.search_metadata(search_query)
            cover_url = meta['cover_url'] if meta else None

            # Actualizar RPC
            self.last_source = "music"
            self.last_media_name = music_info['title']
            self.last_artist = music_info['artist']
            
            logging.info(f"🎵 Music Detected: {music_info['title']} - {music_info['artist']}")

            large_img = cover_url if cover_url else "music_icon"
            
            self.rpc.update(
                activity_type=ActivityType.LISTENING,
                details=music_info['title'],
                state=music_info['artist'],
                large_image=large_img,
            )
            return True
        
            return True
            
        return False
            
        return False

    def _cleanup_rpc(self):
        """Limpia o cierra la conexión RPC si no hay actividad."""
        # Limpiamos si hay alguna fuente activa previa
        if self.last_source:
            if self.rpc:
                try:
                    self.rpc.clear()
                except: pass
            self.last_source = None

    def run_logic(self):
        logging.info(f"🚀 Media RPC {config_manager.APP_VERSION} Started")

        while self.running:
            # 1. Recargar Configuración Dinámica
            self.config = config_manager.cargar_config()

            # 2. Chequear Flag de Reinicio
            flag_path = os.path.join(os.path.dirname(config_manager.PATH_CONFIG), "rpc_restart.flag")
            if os.path.exists(flag_path):
                logging.info("♻️ Restarting RPC by user request...")
                try:
                    if self.rpc: 
                        self.rpc.close()
                        self.rpc = None
                    os.remove(flag_path)
                except: pass

            try:
                # [MODIFICADO] PRIORIDAD: EXTENSIÓN > MÚSICA
                extension_active = self._handle_extension_rpc()
                
                # Check if extension is connected (alive recently)
                is_ext_active_or_connected = False
                if self.extension_info and (time.time() - self.extension_info["timestamp"] < 10):
                    is_ext_active_or_connected = True

                music_active = False
                # Solo chequeamos SMTC si la extensión NO está presente ni activa
                if not extension_active and not is_ext_active_or_connected:
                    music_active = self._handle_music_rpc()
                
                # C. Limpieza
                if not extension_active and not music_active:
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
