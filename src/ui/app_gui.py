import os
import sys
import math
import struct
import customtkinter as ctk
from tkinter import messagebox, simpledialog, filedialog

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import RectangleSelector

import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask

import geopandas as gpd


# =========================
# RUTAS DEL PROYECTO
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.path.join(BASE_DIR, "outputs", "dem")

DEM_PATH = os.path.join(OUT_DIR, "ecuador_display_clipped.tif")       # DEM grande (no lo subiste, pero existe en tu PC)
BORDER_PATH = os.path.join(DATA_DIR, "ecuador.geojson")    # contorno Ecuador

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# =========================
# UTILIDADES: GEOJSON (sin Galápagos)
# =========================
def load_ecuador_mainland_geometry(geojson_path: str):
    """
    Carga Ecuador y se queda SOLO con el polígono más grande (continental),
    lo cual elimina Galápagos (generalmente vienen como geometrías separadas).
    """
    gdf = gpd.read_file(geojson_path)

    # Si viene con varias features, disolvemos todo
    geom = gdf.unary_union

    # Si es MultiPolygon, elegir el de mayor "area" (en grados^2, suficiente para diferenciar Galápagos)
    if geom.geom_type == "MultiPolygon":
        mainland = max(list(geom.geoms), key=lambda g: g.area)
        return mainland

    return geom


# =========================
# UTILIDADES: BILINEAR DOWNSAMPLE (sin scipy)
# =========================
def bilinear_resize(arr: np.ndarray, new_h: int, new_w: int) -> np.ndarray:
    """
    Redimensiona usando interpolación bilineal (pure numpy).
    Funciona con NaN: se recomienda reemplazar NaN antes o enmascarar.
    """
    h, w = arr.shape
    if h == new_h and w == new_w:
        return arr.copy()

    # coordenadas destino -> origen
    y = np.linspace(0, h - 1, new_h)
    x = np.linspace(0, w - 1, new_w)

    x0 = np.floor(x).astype(int)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y0 = np.floor(y).astype(int)
    y1 = np.clip(y0 + 1, 0, h - 1)

    # pesos
    wx = x - x0
    wy = y - y0

    # interpolación en x
    Ia = arr[:, x0]
    Ib = arr[:, x1]
    Ix = (1 - wx) * Ia + wx * Ib  # (h, new_w)

    # interpolación en y (sobre Ix)
    I0 = Ix[y0, :]
    I1 = Ix[y1, :]
    out = (1 - wy)[:, None] * I0 + wy[:, None] * I1
    return out.astype(np.float32)


# =========================
# UTILIDADES: EXPORT STL (SÓLIDO MANIFOLD)
# =========================
class STLExporter:
    """
    Exporta una grilla de alturas a un STL sólido:
    - Top surface
    - Bottom (z=0)
    - Side walls
    """
    @staticmethod
    def _normal(v0, v1, v2):
        a = v1 - v0
        b = v2 - v0
        n = np.cross(a, b)
        norm = np.linalg.norm(n)
        if norm == 0:
            return np.array([0.0, 0.0, 0.0], dtype=np.float32)
        return (n / norm).astype(np.float32)

    @staticmethod
    def export_grid_solid_to_stl(
        z: np.ndarray,
        out_path: str,
        cell_size_mm: float = 1.0,
        base_thickness_mm: float = 2.0,
        height_mm: float = 30.0,
        fill_nan_with_min: bool = True
    ):
        """
        z: matriz elevación en metros (o unidades), con NaN afuera.
        Se normaliza a [base_thickness, base_thickness+height_mm]
        y se crea un sólido cerrado.
        """
        if z.ndim != 2:
            raise ValueError("z debe ser una matriz 2D")

        zz = z.astype(np.float32)

        valid = ~np.isnan(zz)
        if valid.sum() == 0:
            raise ValueError("La zona no tiene datos válidos (todo NaN).")

        zmin = float(np.nanmin(zz))
        zmax = float(np.nanmax(zz))
        if zmax - zmin < 1e-6:
            # todo plano
            zscaled = np.full_like(zz, base_thickness_mm, dtype=np.float32)
        else:
            zscaled = (zz - zmin) / (zmax - zmin)  # 0..1
            zscaled = base_thickness_mm + zscaled * height_mm

        if fill_nan_with_min:
            zscaled[~valid] = base_thickness_mm  # “piso” afuera

        h, w = zscaled.shape

        # Coordenadas XY (mm)
        xs = np.arange(w, dtype=np.float32) * cell_size_mm
        ys = np.arange(h, dtype=np.float32) * cell_size_mm

        # Centramos para que caiga en el centro de la placa
        xs = xs - xs.mean()
        ys = ys - ys.mean()

        # Triangles list: cada tri -> (normal, v0, v1, v2)
        triangles = []

        def vtx(i, j, top=True):
            x = xs[j]
            y = ys[i]
            zval = float(zscaled[i, j]) if top else 0.0
            return np.array([x, y, zval], dtype=np.float32)

        # --- TOP ---
        for i in range(h - 1):
            for j in range(w - 1):
                v00 = vtx(i, j, True)
                v10 = vtx(i + 1, j, True)
                v01 = vtx(i, j + 1, True)
                v11 = vtx(i + 1, j + 1, True)

                # dos tri (orientación hacia arriba)
                n1 = STLExporter._normal(v00, v10, v01)
                triangles.append((n1, v00, v10, v01))

                n2 = STLExporter._normal(v10, v11, v01)
                triangles.append((n2, v10, v11, v01))

        # --- BOTTOM (invertido para que normal apunte hacia abajo) ---
        for i in range(h - 1):
            for j in range(w - 1):
                v00 = vtx(i, j, False)
                v10 = vtx(i + 1, j, False)
                v01 = vtx(i, j + 1, False)
                v11 = vtx(i + 1, j + 1, False)

                n1 = STLExporter._normal(v00, v01, v10)
                triangles.append((n1, v00, v01, v10))

                n2 = STLExporter._normal(v10, v01, v11)
                triangles.append((n2, v10, v01, v11))

        # --- SIDE WALLS (perímetro) ---
        def add_wall(p0_top, p1_top, p0_bot, p1_bot):
            # dos tri para el quad, orientación hacia afuera depende del borde
            n1 = STLExporter._normal(p0_bot, p1_bot, p1_top)
            triangles.append((n1, p0_bot, p1_bot, p1_top))

            n2 = STLExporter._normal(p0_bot, p1_top, p0_top)
            triangles.append((n2, p0_bot, p1_top, p0_top))

        # borde superior i=0
        i = 0
        for j in range(w - 1):
            add_wall(vtx(i, j, True), vtx(i, j + 1, True), vtx(i, j, False), vtx(i, j + 1, False))
        # borde inferior i=h-1
        i = h - 1
        for j in range(w - 1):
            # invertir para mantener “afuera”
            add_wall(vtx(i, j + 1, True), vtx(i, j, True), vtx(i, j + 1, False), vtx(i, j, False))

        # borde izquierdo j=0
        j = 0
        for i in range(h - 1):
            add_wall(vtx(i + 1, j, True), vtx(i, j, True), vtx(i + 1, j, False), vtx(i, j, False))
        # borde derecho j=w-1
        j = w - 1
        for i in range(h - 1):
            add_wall(vtx(i, j, True), vtx(i + 1, j, True), vtx(i, j, False), vtx(i + 1, j, False))

        # --- Escribir STL binario ---
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            header = b"Ecuador DEM solid STL".ljust(80, b" ")
            f.write(header)
            f.write(struct.pack("<I", len(triangles)))

            for (n, a, b, c) in triangles:
                f.write(struct.pack("<3f", float(n[0]), float(n[1]), float(n[2])))
                f.write(struct.pack("<3f", float(a[0]), float(a[1]), float(a[2])))
                f.write(struct.pack("<3f", float(b[0]), float(b[1]), float(b[2])))
                f.write(struct.pack("<3f", float(c[0]), float(c[1]), float(c[2])))
                f.write(struct.pack("<H", 0))

        return out_path


# =========================
# LECTURA EFICIENTE DE ROI (sin cargar todo)
# =========================
def read_dem_roi_masked(
    dem_path: str,
    geojson_path: str,
    bounds_lonlat: tuple[float, float, float, float],
):
    """
    Lee un ROI del DEM usando Window (eficiente RAM),
    y aplica máscara del Ecuador continental (sin Galápagos).
    Devuelve (arr, transform).
    """
    minx, miny, maxx, maxy = bounds_lonlat

    mainland = load_ecuador_mainland_geometry(geojson_path)

    with rasterio.open(dem_path) as src:
        win = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        win = win.round_offsets().round_lengths()

        arr = src.read(1, window=win).astype(np.float32)
        transform = src.window_transform(win)

        # nodata -> NaN
        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan

        # máscara Ecuador continental
        mask = geometry_mask(
            [mainland],
            out_shape=arr.shape,
            transform=transform,
            invert=True  # True = dentro del polígono
        )
        arr[~mask] = np.nan

    return arr, transform


# =========================
# GUI PRINCIPAL
# =========================
class EcuadorMapVisor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Visor Topográfico de Ecuador Continental - Grupo 4")
        self.geometry("1400x900")

        self.selected_bounds = None  # (minx, miny, maxx, maxy)
        self.rect_selector = None

        self.setup_ui()
        self.load_full_map()

    def setup_ui(self):
        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="MENÚ GEOGRÁFICO", font=("Arial", 22, "bold")).pack(pady=20)

        ctk.CTkLabel(self.sidebar, text="Visualizar por Región:", font=("Arial", 14)).pack(pady=(10, 5))
        ctk.CTkButton(self.sidebar, text="Todo el Ecuador", font=("Arial", 13),
                      command=self.load_full_map).pack(pady=8, padx=25, fill="x")

        ctk.CTkLabel(self.sidebar, text="Configuraciones", font=("Arial", 16, "bold")).pack(pady=(25, 10))

        ctk.CTkButton(self.sidebar, text="Zoom", command=self.enable_zoom).pack(pady=6, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="Mover (Pan)", command=self.enable_pan).pack(pady=6, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="Seleccionar zona (rectángulo)", command=self.enable_rect_select).pack(pady=6, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="Recortar por coordenadas", command=self.crop_by_coordinates).pack(pady=6, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="Exportar zona a STL (3D)", command=self.export_selected_to_stl).pack(pady=10, padx=25, fill="x")

        self.status_label = ctk.CTkLabel(self.sidebar, text="Estado: listo.", text_color="gray", font=("Arial", 11))
        self.status_label.pack(side="bottom", pady=20)

        # Map container
        self.map_container = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.map_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.fig, self.ax = plt.subplots(figsize=(10, 10), facecolor="#1a1a1a")
        self.ax.set_facecolor("#000000")
        self.ax.tick_params(colors="white", labelsize=9)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toolbar_frame = ctk.CTkFrame(self.map_container, height=40, fg_color="transparent")
        self.toolbar_frame.pack(side="bottom", fill="x")
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.update()

        self.colorbar = None

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        # Evita errores de "invalid command name ... after script"
        try:
            if self.rect_selector is not None:
                self.rect_selector.set_active(False)
        except:
            pass
        self.destroy()

    # =========================
    # VISUALIZACIÓN
    # =========================
    def load_full_map(self):
        if not os.path.exists(DEM_PATH):
            messagebox.showerror("Falta DEM", f"No existe:\n{DEM_PATH}")
            return
        if not os.path.exists(BORDER_PATH):
            messagebox.showerror("Falta GeoJSON", f"No existe:\n{BORDER_PATH}")
            return

        self.ax.clear()
        self.ax.set_title("Mapa de Elevación - Todo el Ecuador", color="white", fontsize=16)
        self.ax.set_xlabel("Longitud (Grados)", color="white")
        self.ax.set_ylabel("Latitud (Grados)", color="white")
        self.ax.grid(True, color="gray", linestyle="--", alpha=0.25)

        # Para mostrar rápido: usamos una vista “display” (downsample) sin cargar todo
        # Cargamos bounds Ecuador y leemos una ventana grande aproximada
        mainland = load_ecuador_mainland_geometry(BORDER_PATH)
        minx, miny, maxx, maxy = mainland.bounds

        arr, transform = read_dem_roi_masked(DEM_PATH, BORDER_PATH, (minx, miny, maxx, maxy))

        # downsample display para que la UI sea fluida
        max_side = 900
        h, w = arr.shape
        scale = max(h, w) / max_side
        if scale > 1:
            new_h = max(200, int(h / scale))
            new_w = max(200, int(w / scale))
            arr_disp = bilinear_resize(np.nan_to_num(arr, nan=np.nanmin(arr)), new_h, new_w)
            # ojo: no re-mascara, solo display (ya fue enmascarado)
        else:
            arr_disp = arr

        extent = [
            minx, maxx,
            miny, maxy
        ]

        img = self.ax.imshow(arr_disp, extent=extent, cmap="terrain", origin="upper")

        # borde
        gdf = gpd.read_file(BORDER_PATH)
        main_geom = load_ecuador_mainland_geometry(BORDER_PATH)
        gpd.GeoSeries([main_geom], crs="EPSG:4326").boundary.plot(ax=self.ax, linewidth=1.5, color="#00E5FF")

        # colorbar única
        if self.colorbar is not None:
            self.colorbar.remove()
            self.colorbar = None
        self.colorbar = self.fig.colorbar(img, ax=self.ax, fraction=0.046, pad=0.04)
        self.colorbar.set_label("Altura [m]", color="white")
        self.colorbar.ax.yaxis.set_tick_params(color="white", labelcolor="white")

        self.canvas.draw()
        self.status_label.configure(text="Estado: mapa cargado. Selecciona zona para exportar STL.")

    # =========================
    # HERRAMIENTAS
    # =========================
    def enable_zoom(self):
        self.toolbar.zoom()
        self.status_label.configure(text="Estado: Zoom activo (toolbar).")

    def enable_pan(self):
        self.toolbar.pan()
        self.status_label.configure(text="Estado: Pan activo (toolbar).")

    def enable_rect_select(self):
        # activa selector de rectángulo sobre el plot
        if self.rect_selector is not None:
            self.rect_selector.set_active(False)

        def onselect(eclick, erelease):
            x1, y1 = eclick.xdata, eclick.ydata
            x2, y2 = erelease.xdata, erelease.ydata
            if None in (x1, y1, x2, y2):
                return
            minx, maxx = sorted([x1, x2])
            miny, maxy = sorted([y1, y2])
            self.selected_bounds = (minx, miny, maxx, maxy)
            self.status_label.configure(text=f"Estado: zona seleccionada ({minx:.3f},{miny:.3f})-({maxx:.3f},{maxy:.3f})")

        self.rect_selector = RectangleSelector(
            self.ax,
            onselect,
            useblit=True,
            button=[1],
            interactive=True
        )
        self.rect_selector.set_active(True)
        self.status_label.configure(text="Estado: selección activa. Arrastra un rectángulo en el mapa.")

    def crop_by_coordinates(self):
        msg = "Ingresa coordenadas en grados (EPSG:4326).\nEj: minLon=-80.5, minLat=-4.5, maxLon=-78.0, maxLat=-2.0"
        messagebox.showinfo("Recorte por coordenadas", msg)

        minx = simpledialog.askfloat("minLon", "minLon (ej -80.5):")
        miny = simpledialog.askfloat("minLat", "minLat (ej -4.5):")
        maxx = simpledialog.askfloat("maxLon", "maxLon (ej -78.0):")
        maxy = simpledialog.askfloat("maxLat", "maxLat (ej -2.0):")

        if None in (minx, miny, maxx, maxy):
            return

        self.selected_bounds = (min(minx, maxx), min(miny, maxy), max(minx, maxx), max(miny, maxy))
        self.status_label.configure(text=f"Estado: zona por coords lista ({self.selected_bounds[0]:.3f},{self.selected_bounds[1]:.3f})-({self.selected_bounds[2]:.3f},{self.selected_bounds[3]:.3f})")

    # =========================
    # EXPORT STL (SÓLIDO)
    # =========================
    def export_selected_to_stl(self):
        if self.selected_bounds is None:
            messagebox.showerror("Error", "Primero selecciona una zona (rectángulo o coordenadas).")
            return

        if not os.path.exists(DEM_PATH):
            messagebox.showerror("Falta DEM", f"No existe:\n{DEM_PATH}")
            return
        if not os.path.exists(BORDER_PATH):
            messagebox.showerror("Falta GeoJSON", f"No existe:\n{BORDER_PATH}")
            return

        # Parámetros (recomendados para que Bambu no sufra)
        target = simpledialog.askinteger("Resolución", "Resolución objetivo (ej 300-600):", initialvalue=450, minvalue=100, maxvalue=1200)
        if target is None:
            return

        base_mm = simpledialog.askfloat("Base", "Grosor de base (mm):", initialvalue=2.0, minvalue=0.5, maxvalue=20.0)
        if base_mm is None:
            return

        height_mm = simpledialog.askfloat("Altura", "Altura del relieve (mm):", initialvalue=35.0, minvalue=5.0, maxvalue=200.0)
        if height_mm is None:
            return

        cell_mm = simpledialog.askfloat("Escala XY", "Tamaño por celda (mm) (1.0 recomendado):", initialvalue=1.0, minvalue=0.2, maxvalue=5.0)
        if cell_mm is None:
            return

        out_path = filedialog.asksaveasfilename(
            defaultextension=".stl",
            filetypes=[("STL", "*.stl")],
            initialfile="zona_exportada.stl"
        )
        if not out_path:
            return

        self.status_label.configure(text="Estado: leyendo DEM (ROI) y preparando STL...")
        self.update_idletasks()

        try:
            arr, _ = read_dem_roi_masked(DEM_PATH, BORDER_PATH, self.selected_bounds)

            # Reemplaza NaN temporal para bilinear (display/export)
            # (afuera del Ecuador se aplana al mínimo válido)
            vmin = float(np.nanmin(arr))
            arr_filled = np.nan_to_num(arr, nan=vmin).astype(np.float32)

            # Downsample (para reducir peso/triángulos)
            h, w = arr_filled.shape
            scale = max(h, w) / target
            if scale > 1:
                new_h = max(50, int(h / scale))
                new_w = max(50, int(w / scale))
                arr_small = bilinear_resize(arr_filled, new_h, new_w)
            else:
                arr_small = arr_filled

            # Exportar STL sólido
            STLExporter.export_grid_solid_to_stl(
                z=arr_small,
                out_path=out_path,
                cell_size_mm=cell_mm,
                base_thickness_mm=base_mm,
                height_mm=height_mm,
                fill_nan_with_min=True
            )

            messagebox.showinfo("Éxito", f"STL exportado correctamente:\n{out_path}\n\nÁbrelo en Bambu Studio.")
            self.status_label.configure(text=f"Estado: STL exportado -> {os.path.basename(out_path)}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar STL:\n{str(e)}")
            self.status_label.configure(text="Estado: error exportando STL.")


if __name__ == "__main__":
    app = EcuadorMapVisor()
    app.mainloop()
