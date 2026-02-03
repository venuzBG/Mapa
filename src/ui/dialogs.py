import customtkinter as ctk
from tkinter import messagebox

class ExportDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Exportar STL (3D)")
        self.geometry("400x500") # Hice la ventana un poco más alta
        self.resizable(False, False)
        
        self.result = None # Aquí guardaremos los datos si el usuario acepta
        
        # Hacemos que la ventana sea modal (bloquea la de atrás)
        self.transient(parent)
        self.grab_set()
        
        # --- TÍTULO ---
        ctk.CTkLabel(self, text="Parámetros de exportación", font=("Arial", 16, "bold")).pack(pady=20)

        # --- CAMPOS DE ENTRADA ---
        self.frame_inputs = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_inputs.pack(fill="both", expand=True, padx=20)
        
        # 1. Resolución
        ctk.CTkLabel(self.frame_inputs, text="Resolución (Tamaño lado mayor, 100-2000):", anchor="w").pack(fill="x", pady=(10, 0))
        self.entry_res = ctk.CTkEntry(self.frame_inputs)
        self.entry_res.insert(0, "450")
        self.entry_res.pack(fill="x", pady=(0, 10))

        # 2. Base
        ctk.CTkLabel(self.frame_inputs, text="Altura Base (mm):", anchor="w").pack(fill="x", pady=(5, 0))
        self.entry_base = ctk.CTkEntry(self.frame_inputs)
        self.entry_base.insert(0, "2.0")
        self.entry_base.pack(fill="x", pady=(0, 10))

        # 3. Altura Relieve
        ctk.CTkLabel(self.frame_inputs, text="Altura Relieve (Montaña más alta, mm):", anchor="w").pack(fill="x", pady=(5, 0))
        self.entry_height = ctk.CTkEntry(self.frame_inputs)
        self.entry_height.insert(0, "35.0")
        self.entry_height.pack(fill="x", pady=(0, 10))

        # 4. Escala Celda
        ctk.CTkLabel(self.frame_inputs, text="Escala XY (mm por celda):", anchor="w").pack(fill="x", pady=(5, 0))
        self.entry_cell = ctk.CTkEntry(self.frame_inputs)
        self.entry_cell.insert(0, "1.0")
        self.entry_cell.pack(fill="x", pady=(0, 10))

        # --- BOTONES (LO QUE FALTABA) ---
        self.frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buttons.pack(side="bottom", fill="x", pady=20, padx=20)
        
        self.btn_cancel = ctk.CTkButton(
            self.frame_buttons, 
            text="Cancelar", 
            fg_color="gray", 
            hover_color="darkgray",
            command=self.on_cancel,
            width=100
        )
        self.btn_cancel.pack(side="left")
        
        self.btn_ok = ctk.CTkButton(
            self.frame_buttons, 
            text="EXPORTAR", 
            fg_color="#00E5FF", 
            text_color="black",
            hover_color="#00B2CC",
            command=self.on_ok,
            width=100
        )
        self.btn_ok.pack(side="right")
        
    def on_ok(self):
        """Valida los datos y cierra"""
        try:
            # Leemos los valores
            target = int(self.entry_res.get())
            base_mm = float(self.entry_base.get())
            height_mm = float(self.entry_height.get())
            cell_mm = float(self.entry_cell.get())
            
            # Guardamos en un diccionario
            self.result = {
                "target": target,
                "base_mm": base_mm,
                "height_mm": height_mm,
                "cell_mm": cell_mm
            }
            # Cerramos la ventana
            self.destroy()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingresa solo números válidos (usa punto . para decimales).")

    def on_cancel(self):
        """Cierra sin guardar nada"""
        self.result = None
        self.destroy()