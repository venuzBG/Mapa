# src/ui/dialogs/bbox_dialog.py
import customtkinter as ctk

class BBoxDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_submit):
        super().__init__(parent)
        self.title("Recorte por coordenadas")
        self.geometry("360x260")
        self.on_submit = on_submit

        ctk.CTkLabel(self, text="Ingrese bbox (lon_min, lat_min, lon_max, lat_max)").pack(pady=10)

        self.e_lon_min = ctk.CTkEntry(self, placeholder_text="lon_min (ej -81.5)")
        self.e_lat_min = ctk.CTkEntry(self, placeholder_text="lat_min (ej -5.2)")
        self.e_lon_max = ctk.CTkEntry(self, placeholder_text="lon_max (ej -75.0)")
        self.e_lat_max = ctk.CTkEntry(self, placeholder_text="lat_max (ej 1.5)")

        for w in [self.e_lon_min, self.e_lat_min, self.e_lon_max, self.e_lat_max]:
            w.pack(fill="x", padx=20, pady=6)

        ctk.CTkButton(self, text="Aceptar", command=self._accept).pack(pady=12)

    def _accept(self):
        try:
            bbox = (
                float(self.e_lon_min.get()),
                float(self.e_lat_min.get()),
                float(self.e_lon_max.get()),
                float(self.e_lat_max.get()),
            )
            self.on_submit(bbox)
            self.destroy()
        except ValueError:
            # si quieres: messagebox aquí
            pass
