import customtkinter as ctk
import config_manager
import utils
import os
import ctypes
from PIL import Image

import webbrowser

# Configuración de Tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue") 

# Colores Stremio
STREMIO_PURPLE = "#5A4FCF"
STREMIO_PURPLE_HOVER = "#483D8B"
STREMIO_BG = "#151515"

# Colores Discord
DISCORD_BG = "#313338" # Fondo oscuro moderno
DISCORD_CARD_BG = "#111214" # Fondo de la tarjeta (perfil)
DISCORD_TEXT_HEADER = "#F2F3F5"
DISCORD_TEXT_NORMAL = "#DBDEE1"

class ConfigWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        try:
            myappid = "anthony.stremio.rpc.v5"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass

        self.current_config = config_manager.cargar_config()

        self.title("Media RPC - Configuración")
        self.geometry("400x450") # [MODIFICADO] Más compacto sin preview
        self.resizable(False, False)

        if os.path.exists(config_manager.PATH_ICON):
            try:
                self.iconbitmap(config_manager.PATH_ICON)
            except:
                pass

        self.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(500, lambda: self.attributes("-topmost", False))

        # --- UI PRINCIPAL (TABS) ---
        self.tabview = ctk.CTkTabview(self, width=380, height=600)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.tabview.configure(segmented_button_selected_color=STREMIO_PURPLE)
        self.tabview.configure(segmented_button_selected_hover_color=STREMIO_PURPLE_HOVER)

        self.tab_config = self.tabview.add("Ajustes")
        self.tab_logs = self.tabview.add("Logs")

        # ==========================================
        #           PESTAÑA CONFIGURACIÓN
        # ==========================================
        
        self.label_title = ctk.CTkLabel(
            self.tab_config, text="Media RPC", font=("Roboto", 24, "bold"), text_color="white"
        )
        self.label_title.pack(pady=(10, 15))

        # OPCIONES SISTEMA
        self.frame_opts = ctk.CTkFrame(self.tab_config, fg_color="transparent")
        self.frame_opts.pack(fill="x", padx=20)

        # Switch: Auto-Start
        self.switch_autostart = ctk.CTkSwitch(
            self.frame_opts, 
            text="Iniciar con Windows",
            progress_color=STREMIO_PURPLE,
            font=("Roboto", 14)
        )
        if utils.check_autostart():
            self.switch_autostart.select()
        self.switch_autostart.pack(anchor="w", pady=10)

        # Switch: Botón
        self.switch_btn = ctk.CTkSwitch(
            self.frame_opts, 
            text="Mostrar Botón 'Buscar Anime'",
            progress_color=STREMIO_PURPLE,
            font=("Roboto", 14)
        )
        if self.current_config.get("show_search_button", True):
            self.switch_btn.select()
        self.switch_btn.pack(anchor="w", pady=10)

        # Switch: Music RPC
        self.switch_music = ctk.CTkSwitch(
            self.frame_opts, 
            text="Activar Detección de Música",
            progress_color=STREMIO_PURPLE,
            font=("Roboto", 14)
        )
        if self.current_config.get("enable_music_rpc", True):
            self.switch_music.select()
        self.switch_music.pack(anchor="w", pady=10)

        # -----------------------

        # Botón Actualizar
        self.btn_update = ctk.CTkButton(
            self.tab_config,
            text="⬇️ Buscar Actualizaciones",
            command=self.buscar_actualizaciones,
            height=35,
            font=("Roboto", 12),
            fg_color="#333333",
            hover_color="#444444"
        )
        self.btn_update.pack(fill="x", padx=20, pady=(20, 5))

        # Botón Reiniciar RPC
        self.btn_restart = ctk.CTkButton(
            self.tab_config,
            text="♻️ Reiniciar Conexión RPC",
            command=self.reiniciar_rpc,
            height=35,
            font=("Roboto", 12),
            fg_color="#333333",
            hover_color="#444444"
        )
        self.btn_restart.pack(fill="x", padx=20, pady=(5, 5))

        # Botón Guardar
        self.btn_save = ctk.CTkButton(
            self.tab_config,
            text="GUARDAR CAMBIOS",
            command=self.guardar_datos,
            height=45,
            font=("Roboto", 15, "bold"),
            fg_color=STREMIO_PURPLE,
            hover_color=STREMIO_PURPLE_HOVER,
            corner_radius=10
        )
        self.btn_save.pack(fill="x", padx=20, pady=(10, 10))

        # Link GitHub
        self.lbl_github = ctk.CTkLabel(
            self.tab_config, 
            text="GitHub / Soporte", 
            font=("Roboto", 11, "underline"),
            text_color="gray",
            cursor="hand2"
        )
        self.lbl_github.pack(side="bottom", pady=10)
        self.lbl_github.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/anthonybuitrago/stremio-discord-rpc"))

        # ==========================================
        #           PESTAÑA LOGS
        # ==========================================
        self.textbox_logs = ctk.CTkTextbox(self.tab_logs, width=300, height=300)
        self.textbox_logs.pack(padx=5, pady=5, fill="both", expand=True)
        
        self.frame_logs_btns = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        self.frame_logs_btns.pack(fill="x", pady=5)

        self.btn_open_logs = ctk.CTkButton(
            self.frame_logs_btns,
            text="📂 Abrir Archivo",
            command=self.abrir_logs_sistema,
            width=140,
            fg_color="#333333",
            hover_color="#444444"
        )
        self.btn_open_logs.pack(side="left", padx=5)

        self.btn_refresh_logs = ctk.CTkButton(
            self.frame_logs_btns,
            text="🔄 Actualizar",
            command=self.cargar_logs,
            width=140,
            fg_color=STREMIO_PURPLE,
            hover_color=STREMIO_PURPLE_HOVER
        )
        self.btn_refresh_logs.pack(side="right", padx=5)
        
        self.cargar_logs()

    def cargar_logs(self):
        self.textbox_logs.configure(state="normal")
        self.textbox_logs.delete("0.0", "end")
        
        if os.path.exists(config_manager.PATH_LOG):
            try:
                with open(config_manager.PATH_LOG, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-50:]
                    self.textbox_logs.insert("0.0", "".join(lines))
            except Exception as e:
                self.textbox_logs.insert("0.0", f"Error leyendo logs: {e}")
        else:
            self.textbox_logs.insert("0.0", "No hay archivo de logs aún.")
            
        self.textbox_logs.see("end")
        self.textbox_logs.configure(state="disabled")
        
        # Feedback visual
        original_text = self.btn_refresh_logs.cget("text")
        self.btn_refresh_logs.configure(text="¡Actualizado!")
        self.after(1000, lambda: self.btn_refresh_logs.configure(text=original_text))

    def abrir_logs_sistema(self):
        if os.path.exists(config_manager.PATH_LOG):
            os.startfile(config_manager.PATH_LOG)

    def reiniciar_rpc(self):
        # Crear flag file para que main.py lo detecte
        flag_path = os.path.join(os.path.dirname(config_manager.PATH_CONFIG), "rpc_restart.flag")
        with open(flag_path, "w") as f:
            f.write("restart")
        
        original_text = self.btn_restart.cget("text")
        self.btn_restart.configure(text="✅ Solicitud Enviada")
        self.after(2000, lambda: self.btn_restart.configure(text=original_text))

    def buscar_actualizaciones(self):
        self.btn_update.configure(text="Buscando...", state="disabled")
        self.update_idletasks()
        
        try:
            # Importamos aquí para evitar ciclos o cargas innecesarias
            import utils 
            # Definimos la versión actual aquí o la importamos de main/config
            CURRENT_VERSION = "v5.3" 
            
            has_update, new_version = utils.check_for_updates(CURRENT_VERSION)
            
            if has_update:
                self.btn_update.configure(text=f"¡Actualizar a {new_version}!", fg_color=STREMIO_PURPLE, state="normal")
                self.btn_update.configure(command=lambda: webbrowser.open("https://github.com/anthonybuitrago/stremio-discord-rpc/releases"))
            else:
                self.btn_update.configure(text=f"Estás actualizado ({CURRENT_VERSION})", fg_color="green", state="normal")
                self.after(3000, lambda: self.btn_update.configure(text="⬇️ Buscar Actualizaciones", fg_color="#333333", command=self.buscar_actualizaciones))
                
        except Exception as e:
            self.btn_update.configure(text="Error al buscar", fg_color="red", state="normal")
            print(f"Error update: {e}")
            self.after(3000, lambda: self.btn_update.configure(text="⬇️ Buscar Actualizaciones", fg_color="#333333"))

    def guardar_datos(self):
        # Solo guardamos lo que el usuario puede tocar
        datos_nuevos = self.current_config.copy()
        datos_nuevos["show_search_button"] = bool(self.switch_btn.get())
        datos_nuevos["enable_music_rpc"] = bool(self.switch_music.get())
        
        # Aseguramos valores por defecto para lo oculto
        datos_nuevos["update_interval"] = 15
        datos_nuevos["fixed_duration_minutes"] = 0

        # Guardar JSON
        config_manager.guardar_config(datos_nuevos)

        # Aplicar Auto-Start real
        deseo_autostart = bool(self.switch_autostart.get())
        utils.set_autostart(deseo_autostart)

        print("Configuración guardada.")
        self.cerrar_ventana()

    def cerrar_ventana(self):
        self.destroy()
        self.quit()


def abrir_ventana():
    app = ConfigWindow()
    app.after(100, app.focus_force)
    app.mainloop()


if __name__ == "__main__":
    abrir_ventana()
