import customtkinter as ctk
import config_manager
import utils
import os
import ctypes

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ConfigWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        try:
            myappid = "anthony.stremio.rpc.v5"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass

        self.current_config = config_manager.cargar_config()

        self.title("Configuración - Stremio RPC")
        self.geometry("400x500")
        self.resizable(False, False)

        if os.path.exists(config_manager.PATH_ICON):
            try:
                self.iconbitmap(config_manager.PATH_ICON)
                self.after(200, lambda: self.iconbitmap(config_manager.PATH_ICON))
            except:
                pass

        self.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(500, lambda: self.attributes("-topmost", False))

        # --- UI ---
        self.label_title = ctk.CTkLabel(
            self, text="Ajustes de Stremio RPC", font=("Roboto", 22, "bold")
        )
        self.label_title.pack(pady=20)

        # ID
        self.lbl_id = ctk.CTkLabel(self, text="Discord Client ID:")
        self.lbl_id.pack(anchor="w", padx=30)
        self.entry_id = ctk.CTkEntry(self, placeholder_text="Ingresa tu ID", width=340)
        self.entry_id.insert(0, self.current_config.get("client_id", ""))
        self.entry_id.pack(pady=(0, 15))

        # Intervalo
        self.lbl_interval = ctk.CTkLabel(
            self,
            text=f"Velocidad de Actualización: {self.current_config.get('update_interval')} seg",
        )
        self.lbl_interval.pack(anchor="w", padx=30)
        self.slider_interval = ctk.CTkSlider(
            self, from_=2, to=30, number_of_steps=28, command=self.update_slider
        )
        self.slider_interval.set(self.current_config.get("update_interval", 5))
        self.slider_interval.pack(fill="x", padx=30, pady=(0, 20))

        # MODO DE TIEMPO
        self.lbl_time = ctk.CTkLabel(
            self, text="Estilo de Tiempo:", font=("Roboto", 14, "bold")
        )
        self.lbl_time.pack(anchor="w", padx=30)

        self.time_mode_var = ctk.StringVar(value="Auto")
        current_fixed = self.current_config.get("fixed_duration_minutes", 0)
        if current_fixed == 24:
            self.time_mode_var.set("Anime")
        elif current_fixed == 0:
            self.time_mode_var.set("Auto")

        self.radio_auto = ctk.CTkRadioButton(
            self,
            text="Automático (API / Real)",
            variable=self.time_mode_var,
            value="Auto",
        )
        self.radio_auto.pack(anchor="w", padx=30, pady=5)

        self.radio_anime = ctk.CTkRadioButton(
            self,
            text="Forzar Anime (24 min)",
            variable=self.time_mode_var,
            value="Anime",
        )
        self.radio_anime.pack(anchor="w", padx=30, pady=5)

        # OPCIONES SISTEMA
        self.lbl_sys = ctk.CTkLabel(
            self, text="Opciones de Sistema:", font=("Roboto", 14, "bold")
        )
        self.lbl_sys.pack(anchor="w", padx=30, pady=(20, 5))

        # Switch: Botón
        self.switch_btn = ctk.CTkSwitch(self, text="Mostrar Botón 'Buscar Anime'")
        if self.current_config.get("show_search_button", True):
            self.switch_btn.select()
        self.switch_btn.pack(anchor="w", padx=30, pady=5)

        # Switch: Auto-Start (Lee el estado real de Windows)
        self.switch_autostart = ctk.CTkSwitch(self, text="Iniciar con Windows")
        if utils.check_autostart():
            self.switch_autostart.select()
        self.switch_autostart.pack(anchor="w", padx=30, pady=5)

        # Botón Guardar
        self.btn_save = ctk.CTkButton(
            self,
            text="GUARDAR CAMBIOS",
            command=self.guardar_datos,
            height=40,
            font=("Roboto", 14, "bold"),
            fg_color="green",
            hover_color="darkgreen",
        )
        self.btn_save.pack(fill="x", padx=30, pady=(30, 10))

    def update_slider(self, value):
        self.lbl_interval.configure(
            text=f"Velocidad de Actualización: {int(value)} seg"
        )

    def guardar_datos(self):
        # Procesar Modo de Tiempo
        modo = self.time_mode_var.get()
        fixed_minutes = 24 if modo == "Anime" else 0

        # Crear diccionario
        datos_nuevos = self.current_config.copy()
        datos_nuevos["client_id"] = self.entry_id.get().strip()
        datos_nuevos["update_interval"] = int(self.slider_interval.get())
        datos_nuevos["show_search_button"] = bool(self.switch_btn.get())
        datos_nuevos["fixed_duration_minutes"] = fixed_minutes

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
