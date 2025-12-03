import asyncio
import logging
import winsdk.windows.media.control as wmc

# Global session manager
_manager = None

async def get_media_info_async():
    """
    Async function to get media info using winsdk.
    """
    global _manager
    try:
        if _manager is None:
            _manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()

        session = _manager.get_current_session()
        if not session:
            return None

        # Filter for YouTube Music (or make it configurable)
        # source_id usually looks like "music.youtube.com-..."
        source_id = session.source_app_user_model_id
        if "music.youtube.com" not in source_id.lower():
            return None

        info = session.get_playback_info()
        props = await session.try_get_media_properties_async()

        if not props:
            return None

        return {
            "title": props.title,
            "artist": props.artist,
            "is_playing": info.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING,
            "status": str(info.playback_status),
            "source": source_id,
            "album_title": "YouTube Music", # Winsdk doesn't always give album reliably for web apps
            "cover_url": None # Retrieving thumbnail is complex (stream), skipping for now
        }

    except Exception as e:
        logging.error(f"Error in winsdk get_media_info: {e}")
        return None

def get_media_info():
    """
    Synchronous wrapper for the async function.
    """
    try:
        # Create a new event loop if there isn't one, or use existing
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If we are already in a loop (unlikely for this simple script structure but possible)
            # We can't block. This might be an issue if main.py was async.
            # But main.py calls this in a loop.
            # For now, let's assume we can run_until_complete.
            future = asyncio.run_coroutine_threadsafe(get_media_info_async(), loop)
            return future.result()
        else:
            return loop.run_until_complete(get_media_info_async())
            
    except Exception as e:
        logging.error(f"Error running async wrapper: {e}")
        return None
