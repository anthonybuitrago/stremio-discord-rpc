import customtkinter as ctk
import config_manager
import os
import ctypes # <--- NECESARIO PARA EL ICONO EN LA BARRA DE TAREAS

# Configuración visual global
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ConfigWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- TRUCO PARA EL ICONO EN LA BARRA DE TAREAS ---
        # Esto le dice a Windows que somos una App propia, no "Python genérico"
        try:
            myappid = 'anthony.stremio.rpc.v1' # Identificador único arbitrario
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except: pass

        # --- CARGAR CONFIGURACIÓN ---
        self.current_config = config_manager.cargar_config()

        # 1. CONFIGURACIÓN DE LA VENTANA
        self.title("Configuración - Stremio RPC")
        self.geometry("500x600")
        self.resizable(False, False)

        # --- ASIGNAR ICONO ---
        if os.path.exists(config_manager.PATH_ICON):
            try:
                self.iconbitmap(config_manager.PATH_ICON)
                # Forzamos actualización del icono
                self.after(200, lambda: self.iconbitmap(config_manager.PATH_ICON)) 
            except: pass

        # --- CONFIGURAR BOTÓN DE CERRAR (X) ---
        self.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)

        # --- FORZAR FOCO (SOLUCIÓN "NO SE SUPERPONE") ---
        self.attributes("-topmost", True) # Poner siempre encima
        self.lift()                       # Levantar ventana
        self.focus_force()                # Forzar foco del teclado
        
        # Quitamos el "siempre encima" después de medio segundo para que no moleste
        self.after(500, lambda: self.attributes("-topmost", False))

        # --- INTERFAZ ---
        
        # Título
        self.label_title = ctk.CTkLabel(self, text="Ajustes de Stremio RPC", font=("Roboto", 24, "bold"))
        self.label_title.pack(pady=20)

        # Campo: Client ID
        self.lbl_id = ctk.CTkLabel(self, text="Discord Client ID:")
        self.lbl_id.pack(anchor="w", padx=20)
        self.entry_id = ctk.CTkEntry(self, placeholder_text="Ingresa tu ID", width=460)
        self.entry_id.insert(0, self.current_config.get("client_id", ""))
        self.entry_id.pack(pady=(0, 10))

        # Campo: Intervalo
        self.lbl_interval = ctk.CTkLabel(self, text=f"Velocidad de Actualización: {self.current_config.get('update_interval')} seg")
        self.lbl_interval.pack(anchor="w", padx=20)
        
        self.slider_interval = ctk.CTkSlider(self, from_=2, to=30, number_of_steps=28, command=self.update_slider_label)
        self.slider_interval.set(self.current_config.get("update_interval", 5))
        self.slider_interval.pack(fill="x", padx=20, pady=(0, 10))

        # Campo: Botón
        self.switch_btn = ctk.CTkSwitch(self, text="Mostrar Botón 'Buscar Anime'")
        if self.current_config.get("show_search_button", True):
            self.switch_btn.select()
        self.switch_btn.pack(anchor="w", padx=20, pady=10)

        # Campo: Lista Negra
        self.lbl_blacklist = ctk.CTkLabel(self, text="Lista Negra (Palabras a borrar, separadas por coma):")
        self.lbl_blacklist.pack(anchor="w", padx=20, pady=(10, 0))
        
        self.txt_blacklist = ctk.CTkTextbox(self, height=150, width=460)
        lista_texto = ", ".join(self.current_config.get("blacklisted_words", []))
        self.txt_blacklist.insert("0.0", lista_texto)
        self.txt_blacklist.pack(pady=(5, 20))

        # Botón Guardar
        self.btn_save = ctk.CTkButton(self, text="GUARDAR Y CERRAR", command=self.guardar_datos, height=40, font=("Roboto", 14, "bold"))
        self.btn_save.pack(fill="x", padx=20, pady=10)

    def update_slider_label(self, value):
        self.lbl_interval.configure(text=f"Velocidad de Actualización: {int(value)} seg")

    def guardar_datos(self):
        # Recolectar datos
        new_id = self.entry_id.get().strip()
        new_interval = int(self.slider_interval.get())
        show_btn = bool(self.switch_btn.get())
        
        raw_text = self.txt_blacklist.get("0.0", "end").replace("\n", "")
        new_blacklist = [palabra.strip() for palabra in raw_text.split(",") if palabra.strip()]

        # Crear diccionario
        datos_nuevos = self.current_config.copy()
        datos_nuevos["client_id"] = new_id
        datos_nuevos["update_interval"] = new_interval
        datos_nuevos["show_search_button"] = show_btn
        datos_nuevos["blacklisted_words"] = new_blacklist

        # Guardar
        config_manager.guardar_config(datos_nuevos)
        print("Configuración guardada.")
        
        # Cerrar Inmediato
        self.cerrar_ventana()

    def cerrar_ventana(self):
        # Destruimos visualmente primero (Sensación de rapidez)
        self.destroy()
        # Luego matamos el loop
        self.quit()

def abrir_ventana():
    app = ConfigWindow()
    # Forzamos el foco otra vez al iniciar el loop
    app.after(100, app.focus_force)
    app.mainloop()

if __name__ == "__main__":
    abrir_ventana()