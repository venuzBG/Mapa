import os
import struct
import customtkinter as ctk
from tkinter import messagebox, filedialog
from dialogs import ExportDialog

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import RectangleSelector

import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask

import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon # <--- NUEVA IMPORTACIÓN NECESARIA

# =========================
# RUTAS DEL PROYECTO
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.path.join(BASE_DIR, "outputs", "dem")

DEM_PATH = os.path.join(OUT_DIR, "ecuador_display_clipped.tif")
BORDER_PATH = os.path.join(DATA_DIR, "ecuador.geojson")     # Borde País
PROVINCES_PATH = os.path.join(DATA_DIR, "provincias.geojson") # Provincias
CANTONES_PATH = os.path.join(DATA_DIR, "cantones.geojson")   # Cantones

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# =========================
# UTILIDADES
# =========================
def load_ecuador_mainland_geometry(geojson_path: str):
    """ 
    Carga el contorno, une todo y ELIMINA LOS AGUJEROS INTERNOS (Slivers)
    para evitar que aparezcan líneas gruesas dentro del mapa.
    """
    try:
        gdf = gpd.read_file(geojson_path)
        
        # 1. Unir todas las geometrías en una sola
        geom = gdf.unary_union

        # 2. Función para borrar agujeros (se queda solo con la cáscara de afuera)
        def drop_holes(geometry):
            if geometry.geom_type == 'Polygon':
                return Polygon(geometry.exterior)
            elif geometry.geom_type == 'MultiPolygon':
                return MultiPolygon([Polygon(p.exterior) for p in geometry.geoms])
            return geometry

        # 3. Aplicar la limpieza
        geom_clean = drop_holes(geom)

        # 4. Quedarse solo con el continente (el polígono más grande)
        if geom_clean.geom_type == "MultiPolygon":
            mainland = max(list(geom_clean.geoms), key=lambda g: g.area)
            return mainland
        
        return geom_clean

    except Exception as e:
        print(f"Error cargando geometría: {e}")
        return None

def bilinear_resize(arr: np.ndarray, new_h: int, new_w: int) -> np.ndarray:
    h, w = arr.shape
    if h == new_h and w == new_w: return arr
    y, x = np.linspace(0, h - 1, new_h), np.linspace(0, w - 1, new_w)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.clip(x0 + 1, 0, w - 1), np.clip(y0 + 1, 0, h - 1)
    wx, wy = x - x0, y - y0
    Ia, Ib = arr[:, x0], arr[:, x1]
    Ix = (1 - wx) * Ia + wx * Ib
    I0, I1 = Ix[y0, :], Ix[y1, :]
    return ((1 - wy)[:, None] * I0 + wy[:, None] * I1).astype(np.float32)

def read_dem_roi_masked(dem_path: str, geojson_path: str, bounds_lonlat: tuple):
    minx, miny, maxx, maxy = bounds_lonlat
    mainland = load_ecuador_mainland_geometry(geojson_path)
    with rasterio.open(dem_path) as src:
        win = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        win = win.round_offsets().round_lengths()
        arr = src.read(1, window=win).astype(np.float32)
        transform = src.window_transform(win)
        if src.nodata is not None: arr[arr == src.nodata] = np.nan
        if mainland:
            mask = geometry_mask([mainland], out_shape=arr.shape, transform=transform, invert=True)
            arr[~mask] = np.nan
    return arr, transform

# =========================
# CLASE EXPORTADOR STL
# =========================
class STLExporter:
    @staticmethod
    def _normal(v0, v1, v2):
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n)
        return (n / norm).astype(np.float32) if norm > 0 else np.zeros(3, dtype=np.float32)

    @staticmethod
    def export_grid_solid_to_stl(z, out_path, cell_size_mm, base_thickness_mm, height_mm, fill_nan_with_min=True):
        zz = z.astype(np.float32)
        valid = ~np.isnan(zz)
        zmin, zmax = np.nanmin(zz), np.nanmax(zz)
        zscaled = np.full_like(zz, base_thickness_mm) if (zmax - zmin < 1e-6) else \
                  (base_thickness_mm + ((zz - zmin) / (zmax - zmin)) * height_mm)
        if fill_nan_with_min: zscaled[~valid] = base_thickness_mm

        h, w = zscaled.shape
        xs = (np.arange(w, dtype=np.float32) * cell_size_mm); xs -= xs.mean()
        ys = (np.arange(h, dtype=np.float32) * cell_size_mm); ys -= ys.mean()

        triangles = []
        def vtx(i, j, top): return np.array([xs[j], ys[i], float(zscaled[i, j]) if top else 0.0], dtype=np.float32)

        for i in range(h - 1):
            for j in range(w - 1):
                vt00, vt10, vt01, vt11 = vtx(i,j,True), vtx(i+1,j,True), vtx(i,j+1,True), vtx(i+1,j+1,True)
                vb00, vb10, vb01, vb11 = vtx(i,j,False), vtx(i+1,j,False), vtx(i,j+1,False), vtx(i+1,j+1,False)
                triangles.extend([
                    (STLExporter._normal(vt00, vt10, vt01), vt00, vt10, vt01),
                    (STLExporter._normal(vt10, vt11, vt01), vt10, vt11, vt01),
                    (STLExporter._normal(vb00, vb01, vb10), vb00, vb01, vb10),
                    (STLExporter._normal(vb10, vb01, vb11), vb10, vb01, vb11)
                ])

        def add_wall(p0t, p1t, p0b, p1b):
            triangles.extend([
                (STLExporter._normal(p0b, p1b, p1t), p0b, p1b, p1t),
                (STLExporter._normal(p0b, p1t, p0t), p0b, p1t, p0t)
            ])
            
        for j in range(w-1): add_wall(vtx(0,j,True), vtx(0,j+1,True), vtx(0,j,False), vtx(0,j+1,False))
        for j in range(w-1): add_wall(vtx(h-1,j+1,True), vtx(h-1,j,True), vtx(h-1,j+1,False), vtx(h-1,j,False))
        for i in range(h-1): add_wall(vtx(i+1,0,True), vtx(i,0,True), vtx(i+1,0,False), vtx(i,0,False))
        for i in range(h-1): add_wall(vtx(i,w-1,True), vtx(i+1,w-1,True), vtx(i,w-1,False), vtx(i+1,w-1,False))

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(b"Ecuador DEM STL".ljust(80, b" "))
            f.write(struct.pack("<I", len(triangles)))
            for n, a, b, c in triangles:
                for p in [n, a, b, c]: f.write(struct.pack("<3f", *p))
                f.write(struct.pack("<H", 0))

# =========================
# GUI PRINCIPAL
# =========================
class EcuadorMapVisor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Visor Ecuador Continental - Grupo 4")
        self.geometry("1400x900")
        self.selected_bounds = None
        self.rect_selector = None
        self.colorbar = None
        self.setup_ui()
        self.load_full_map()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="CONTROLES", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkButton(self.sidebar, text="Restablecer Vista", command=self.load_full_map).pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.sidebar, text="Herramientas", font=("Arial", 14, "bold")).pack(pady=(20,10))
        ctk.CTkButton(self.sidebar, text="Zoom", command=lambda: [self.toolbar.zoom(), self.status("Zoom activo")]).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="Mover (Pan)", command=lambda: [self.toolbar.pan(), self.status("Mover activo")]).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="Seleccionar Zona", command=self.enable_rect_select).pack(pady=5, padx=20, fill="x")
        
        ctk.CTkButton(self.sidebar, text="EXPORTAR STL", command=self.export_stl, fg_color="#D00000", hover_color="#800000").pack(pady=30, padx=20, fill="x")
        
        self.status_lbl = ctk.CTkLabel(self.sidebar, text="Listo.", text_color="gray")
        self.status_lbl.pack(side="bottom", pady=20)

        self.map_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.map_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.fig, self.ax = plt.subplots(figsize=(8,8), facecolor="#1a1a1a")
        self.ax.set_facecolor("black")
        self.ax.tick_params(colors="white")
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, ctk.CTkFrame(self.map_frame))
        self.toolbar.update()
        
    def status(self, txt): self.status_lbl.configure(text=txt)

    def load_full_map(self):
        if not os.path.exists(DEM_PATH):
            messagebox.showerror("Error", "Falta el archivo DEM.")
            return

        self.ax.clear()
        self.ax.set_title("Ecuador Continental (Sin Galápagos)", color="white", fontsize=14)
        self.ax.grid(False)

        # 1. Obtener límites SOLO del continente (LIMPIO DE AGUJEROS)
        mainland = load_ecuador_mainland_geometry(BORDER_PATH)
        bounds = mainland.bounds if mainland else (-81.5, -5.5, -75.0, 1.5)
        
        # 2. Cargar DEM Recortado
        arr, _ = read_dem_roi_masked(DEM_PATH, BORDER_PATH, bounds)
        
        # 3. Mostrar Imagen
        h, w = arr.shape
        scale = max(h,w)/800
        arr_disp = bilinear_resize(np.nan_to_num(arr, nan=np.nanmin(arr)), int(h/scale), int(w/scale)) if scale > 1 else arr
        
        img = self.ax.imshow(arr_disp, extent=[bounds[0], bounds[2], bounds[1], bounds[3]], cmap="terrain", origin="upper")
        
        # 4. Dibujar Líneas
        try:
            # Cantones (Finitos)
            f_cant = CANTONES_PATH if os.path.exists(CANTONES_PATH) else BORDER_PATH
            gpd.read_file(f_cant).boundary.plot(ax=self.ax, linewidth=0.3, color="white", alpha=0.4)
            
            # Provincias (Medio)
            if os.path.exists(PROVINCES_PATH):
                gpd.read_file(PROVINCES_PATH).boundary.plot(ax=self.ax, linewidth=0.8, color="white", alpha=0.8)
            
            # Borde País (Grueso) - AHORA SOLO DIBUJARÁ EL BORDE EXTERIOR REAL
            if mainland:
                gpd.GeoSeries([mainland]).boundary.plot(ax=self.ax, linewidth=2.0, color="#00E5FF")
        except: pass

        # --- RECORTE DE CÁMARA ---
        self.ax.set_xlim(bounds[0], bounds[2])
        self.ax.set_ylim(bounds[1], bounds[3])

        # --- BARRA DE COLORES ---
        if self.colorbar: 
            try: self.colorbar.remove()
            except: pass
            
        self.colorbar = self.fig.colorbar(img, ax=self.ax, fraction=0.046, pad=0.04)
        self.colorbar.set_label("Altura [m]", color="white")
        self.colorbar.ax.yaxis.set_tick_params(color="white", labelcolor="white")
        self.colorbar.outline.set_edgecolor('white')

        self.canvas.draw()
        self.status("Mapa Continental Cargado.")

    def enable_rect_select(self):
        if self.rect_selector: self.rect_selector.set_active(False)
        def onselect(eclick, erelease):
            x1, y1, x2, y2 = eclick.xdata, eclick.ydata, erelease.xdata, erelease.ydata
            self.selected_bounds = (min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2))
            self.status("Zona seleccionada.")
        self.rect_selector = RectangleSelector(self.ax, onselect, useblit=True, button=[1], interactive=True)
        self.rect_selector.set_active(True)
        self.status("Selecciona una zona...")

    def export_stl(self):
        if not self.selected_bounds: return messagebox.showwarning("!", "Selecciona una zona primero.")
        dlg = ExportDialog(self)
        self.wait_window(dlg)
        if not dlg.result: return
        
        fpath = filedialog.asksaveasfilename(defaultextension=".stl", filetypes=[("STL","*.stl")])
        if not fpath: return
        
        self.status("Generando STL...")
        self.update_idletasks()
        try:
            arr, _ = read_dem_roi_masked(DEM_PATH, BORDER_PATH, self.selected_bounds)
            arr_filled = np.nan_to_num(arr, nan=np.nanmin(arr))
            scale = max(arr_filled.shape) / dlg.result["target"]
            h, w = arr_filled.shape
            arr_final = bilinear_resize(arr_filled, int(h/scale), int(w/scale)) if scale > 1 else arr_filled
            
            STLExporter.export_grid_solid_to_stl(arr_final, fpath, dlg.result["cell_mm"], dlg.result["base_mm"], dlg.result["height_mm"])
            messagebox.showinfo("OK", "STL Listo.")
            self.status("Listo.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status("Error.")

if __name__ == "__main__":
    app = EcuadorMapVisor()
    app.mainloop()