# src/ui/dialogs.py
import customtkinter as ctk
from tkinter import messagebox


class ExportDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Exportar STL (3D)")
        self.geometry("360x320")
        self.resizable(False, False)

        self.result = None

        ctk.CTkLabel(
            self,
            text="Parámetros de exportación",
            font=("Arial", 16, "bold")
        ).pack(pady=12)

        self.target_var = ctk.IntVar(value=450)
        self.base_var = ctk.DoubleVar(value=2.0)
        self.height_var = ctk.DoubleVar(value=35.0)
        self.cell_var = ctk.DoubleVar(value=1.0)

        self._row("Resolución (100-1200)", self.target_var)
        self._row("Base (mm)", self.base_var)
        self._row("Altura relieve (mm)", self.height_var)
        self._row("Escala XY (mm/celda)", self.cell_var)

        # Botones
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=15, fill="x", padx=16)

        ctk.CTkButton(btns, text="Cancelar", command=self._cancel).pack(
            side="left", expand=True, padx=6
        )
        ctk.CTkButton(btns, text="Aceptar", command=self._ok).pack(
            side="left", expand=True, padx=6
        )

        # Atajos de teclado
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

        self.grab_set()  # modal

    def _row(self, label, var):
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(box, text=label).pack(anchor="w")
        ctk.CTkEntry(box, textvariable=var).pack(fill="x")

    def _ok(self):
        try:
            target = int(self.target_var.get())
            base = float(self.base_var.get())
            height = float(self.height_var.get())
            cell = float(self.cell_var.get())

            if not (100 <= target <= 1200):
                raise ValueError("Resolución fuera de rango (100-1200).")
            if not (0.5 <= base <= 20.0):
                raise ValueError("Base fuera de rango (0.5-20 mm).")
            if not (5.0 <= height <= 200.0):
                raise ValueError("Altura fuera de rango (5-200 mm).")
            if not (0.2 <= cell <= 5.0):
                raise ValueError("Celda fuera de rango (0.2-5 mm).")

            self.result = {
                "target": target,
                "base_mm": base,
                "height_mm": height,
                "cell_mm": cell,
            }
            self.destroy()

        except Exception as e:
            messagebox.showerror("Valores inválidos", str(e))

    def _cancel(self):
        self.result = None
        self.destroy()
