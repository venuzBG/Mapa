# src/ui/dialogs.py
import customtkinter as ctk

class ExportDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Exportar STL (3D)")
        self.geometry("360x320")
        self.resizable(False, False)

        self.result = None

        ctk.CTkLabel(self, text="Parámetros de exportación", font=("Arial", 16, "bold")).pack(pady=12)

        self.target_var = ctk.IntVar(value=450)
        self.base_var = ctk.DoubleVar(value=2.0)
        self.height_var = ctk.DoubleVar(value=35.0)
        self.cell_var = ctk.DoubleVar(value=1.0)

        self._row("Resolución (100-1200)", self.target_var)
        self._row("Base (mm)", self.base_var)
        self._row("Altura relieve (mm)", self.height_var)
        self._row("Escala XY (mm/celda)", self.cell_var)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=15, fill="x", padx=16)

        ctk.CTkButton(btns, text="Cancelar", command=self._cancel).pack(side="left", expand=True, padx=6)
        ctk.CTkButton(btns, text="Aceptar", command=self._ok).pack(side="left", expand=True, padx=6)

        self.grab_set()  # modal

    def _row(self, label, var):
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(box, text=label).pack(anchor="w")
        ctk.CTkEntry(box, textvariable=var).pack(fill="x")

    def _ok(self):
        self.result = {
            "target": int(self.target_var.get()),
            "base_mm": float(self.base_var.get()),
            "height_mm": float(self.height_var.get()),
            "cell_mm": float(self.cell_var.get()),
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()
