import logging
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# Disable Flask banner
import sys
import os

app = Flask(__name__)
CORS(app) # Enable CORS for extension

# Global callback to update the main client
_update_callback = None

@app.route('/update', methods=['POST'])
def update_media():
    data = request.json
    if _update_callback:
        _update_callback(data)
    return jsonify({"status": "ok"})

def run_flask():
    try:
        # Suppress Flask logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        
        app.run(host='127.0.0.1', port=9696, debug=False, use_reloader=False)
    except Exception as e:
        logging.error(f"Error starting server: {e}")

def start_server(callback):
    """
    Starts the Flask server in a background thread.
    callback: function that accepts a dict (data from extension)
    """
    global _update_callback
    _update_callback = callback
    
    thread = threading.Thread(target=run_flask, daemon=True)
    thread.start()
    logging.info("🌐 Servidor de extensión iniciado en puerto 9696")
