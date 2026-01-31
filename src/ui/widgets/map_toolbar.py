# src/ui/widgets/map_toolbar.py
import customtkinter as ctk

class MapToolbar(ctk.CTkFrame):
    def __init__(self, parent, mpl_toolbar, on_select_rect, on_select_coords, on_export_stl):
        super().__init__(parent)
        self.mpl_toolbar = mpl_toolbar

        ctk.CTkLabel(self, text="Configuraciones", font=("Arial", 16, "bold")).pack(pady=(10, 10))

        ctk.CTkButton(self, text="Zoom", command=self._zoom).pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(self, text="Mover (Pan)", command=self._pan).pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(self, text="Seleccionar zona (rectángulo)", command=on_select_rect).pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(self, text="Recortar por coordenadas", command=on_select_coords).pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(self, text="Exportar zona a STL (3D)", command=on_export_stl).pack(fill="x", padx=10, pady=10)

    def _zoom(self):
        self.mpl_toolbar.zoom()

    def _pan(self):
        self.mpl_toolbar.pan()
