import os
import sys
import numpy as np
import customtkinter as ctk
from tkinter import messagebox

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import RectangleSelector

import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling

import geopandas as gpd


# -----------------------------
# Paths (PRO)
# -----------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

DEM_DIR = os.path.join(ROOT_DIR, "outputs", "dem")
DATA_DIR = os.path.join(ROOT_DIR, "data")

DEFAULT_DEM = os.path.join(DEM_DIR, "ecuador_display_clipped.tif")  # versión liviana para GUI
DEFAULT_BORDER = os.path.join(DATA_DIR, "ecuador.geojson")


# -----------------------------
# Small helpers (embedded)
# (luego si quieres los movemos a src/processing, src/ui/dialogs, etc.)
# -----------------------------
def remove_galapagos(gdf, lon_cutoff=-86.0):
    """Quita Galápagos usando la longitud del centroide."""
    kept = []
    for geom in gdf.geometry:
        if geom is None:
            continue
        parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in parts:
            if p.centroid.x > lon_cutoff:
                kept.append(p)

    # crea un GeoDataFrame con solo mainland
    out = gdf.iloc[:0].copy()
    out["geometry"] = kept
    out = out.set_crs(gdf.crs)
    return out


class BBoxDialog(ctk.CTkToplevel):
    """Dialogo para bbox en coordenadas: lon_min, lat_min, lon_max, lat_max"""
    def __init__(self, parent, on_submit):
        super().__init__(parent)
        self.on_submit = on_submit

        self.title("Recorte por coordenadas")
        self.geometry("380x270")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="Ingrese bbox (lon_min, lat_min, lon_max, lat_max)",
                     font=("Arial", 13, "bold")).pack(pady=(12, 8))

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
            lon_min, lat_min, lon_max, lat_max = bbox
            if lon_min >= lon_max or lat_min >= lat_max:
                raise ValueError("BBox inválido: min debe ser menor que max.")
            self.on_submit(bbox)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Coordenadas inválidas.\n{e}")


class STLExporter:
    """Export STL ASCII (superficie) desde una matriz Z."""
    def __init__(self, z_scale=1.0, xy_scale=1.0):
        self.z_scale = float(z_scale)
        self.xy_scale = float(xy_scale)

    def grid_to_triangles(self, Z: np.ndarray):
        h, w = Z.shape
        tris = []

        for i in range(h - 1):
            for j in range(w - 1):
                z00 = Z[i, j]
                z10 = Z[i + 1, j]
                z01 = Z[i, j + 1]
                z11 = Z[i + 1, j + 1]

                if np.isnan([z00, z10, z01, z11]).any():
                    continue

                x0, x1 = j * self.xy_scale, (j + 1) * self.xy_scale
                y0, y1 = i * self.xy_scale, (i + 1) * self.xy_scale

                z00 *= self.z_scale
                z10 *= self.z_scale
                z01 *= self.z_scale
                z11 *= self.z_scale

                v00 = (x0, y0, z00)
                v10 = (x0, y1, z10)
                v01 = (x1, y0, z01)
                v11 = (x1, y1, z11)

                # dos triángulos por celda
                tris.append((v00, v10, v01))
                tris.append((v10, v11, v01))

        return tris

    def write_ascii_stl(self, triangles, out_path: str, name="terrain"):
        def normal(v1, v2, v3):
            a = np.array(v2) - np.array(v1)
            b = np.array(v3) - np.array(v1)
            n = np.cross(a, b)
            norm = np.linalg.norm(n)
            return (n / norm) if norm != 0 else np.array([0.0, 0.0, 0.0])

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"solid {name}\n")
            for v1, v2, v3 in triangles:
                n = normal(v1, v2, v3)
                f.write(f"  facet normal {n[0]} {n[1]} {n[2]}\n")
                f.write("    outer loop\n")
                f.write(f"      vertex {v1[0]} {v1[1]} {v1[2]}\n")
                f.write(f"      vertex {v2[0]} {v2[1]} {v2[2]}\n")
                f.write(f"      vertex {v3[0]} {v3[1]} {v3[2]}\n")
                f.write("    endloop\n")
                f.write("  endfacet\n")
            f.write(f"endsolid {name}\n")


def crop_window_from_tif(tif_path, bbox, out_shape=None, resampling=Resampling.bilinear):
    """
    Recorta SOLO una ventana del GeoTIFF (RAM friendly)
    bbox = (lon_min, lat_min, lon_max, lat_max)
    out_shape=(h,w) si quieres downsample sin cargar todo.
    """
    lon_min, lat_min, lon_max, lat_max = bbox
    with rasterio.open(tif_path) as src:
        window = from_bounds(lon_min, lat_min, lon_max, lat_max, transform=src.transform)
        window = window.round_offsets().round_lengths()

        if out_shape is None:
            arr = src.read(1, window=window)
            transform = src.window_transform(window)
        else:
            arr = src.read(1, window=window, out_shape=out_shape, resampling=resampling)
            transform = src.window_transform(window)

        nodata = src.nodata

    arr = arr.astype(np.float32)
    if nodata is not None:
        arr[arr == nodata] = np.nan
    return arr, transform


# -----------------------------
# App
# -----------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class EcuadorMapVisor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Visor Topográfico de Ecuador Continental - Grupo 4")
        self.geometry("1400x900")
        self.minsize(1200, 750)

        # estado
        self.current_bbox = None
        self.selector = None
        self._selection_patch = None

        # regiones (por ahora solo 1, como dijiste)
        self.regiones = {
            "Todo el Ecuador": "ecuador_display_clipped.tif",
        }

        self._build_ui()

    def _build_ui(self):
        # Grid principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(99, weight=1)

        ctk.CTkLabel(self.sidebar, text="MENÚ GEOGRÁFICO", font=("Arial", 22, "bold")).pack(pady=18)

        ctk.CTkLabel(self.sidebar, text="Visualizar por Región:", font=("Arial", 14)).pack(pady=(10, 5))

        for region in self.regiones.keys():
            ctk.CTkButton(
                self.sidebar, text=region, font=("Arial", 13),
                command=lambda r=region: self.load_region(r)
            ).pack(pady=8, padx=25, fill="x")

        # ---- Configuraciones (lo que pediste) ----
        ctk.CTkLabel(self.sidebar, text="Configuraciones", font=("Arial", 16, "bold")).pack(pady=(18, 10))

        ctk.CTkButton(self.sidebar, text="Zoom", command=self._do_zoom).pack(pady=6, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="Mover (Pan)", command=self._do_pan).pack(pady=6, padx=25, fill="x")

        ctk.CTkButton(self.sidebar, text="Seleccionar zona (rectángulo)", command=self._enable_rect_select)\
            .pack(pady=6, padx=25, fill="x")

        ctk.CTkButton(self.sidebar, text="Recortar por coordenadas", command=self._open_bbox_dialog)\
            .pack(pady=6, padx=25, fill="x")

        ctk.CTkButton(self.sidebar, text="Exportar zona a STL (3D)", command=self._export_selected_zone_stl)\
            .pack(pady=(10, 6), padx=25, fill="x")

        # status
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="Estado: listo",
            text_color="gray",
            font=("Arial", 11),
            wraplength=260,
            justify="left"
        )
        self.status_label.pack(pady=(18, 0), padx=20)

        # Map container
        self.map_container = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.map_container.grid(row=0, column=1, padx=18, pady=18, sticky="nsew")
        self.map_container.grid_rowconfigure(0, weight=1)
        self.map_container.grid_columnconfigure(0, weight=1)

        # Matplotlib fig/ax
        self.fig, self.ax = plt.subplots(figsize=(10, 10), facecolor="#1a1a1a")
        self.ax.set_facecolor("#000000")
        self.ax.tick_params(colors="white", labelsize=9)
        self.ax.set_title("Seleccione una región en el menú lateral", color="white", pad=18)

        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_container)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Toolbar (matplotlib)
        self.toolbar_frame = ctk.CTkFrame(self.map_container, height=40, fg_color="transparent")
        self.toolbar_frame.grid(row=1, column=0, sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.update()

        self.colorbar = None

    # -----------------------------
    # Map Loading
    # -----------------------------
    def load_region(self, region_name: str):
        self.status_label.configure(text=f"Estado: cargando {region_name}...")
        self.ax.clear()
        self._clear_selection_overlay()

        tif_name = self.regiones[region_name]
        tif_path = os.path.join(DEM_DIR, tif_name)

        if not os.path.exists(tif_path):
            messagebox.showerror("Error", f"No existe el archivo:\n{tif_path}")
            self.status_label.configure(text="Estado: error (archivo no encontrado)")
            return

        # cargar frontera
        border_path = DEFAULT_BORDER
        if not os.path.exists(border_path):
            messagebox.showerror("Error", f"No existe el archivo de frontera:\n{border_path}")
            self.status_label.configure(text="Estado: error (frontera no encontrada)")
            return

        try:
            ecu = gpd.read_file(border_path)
            ecu = ecu.set_crs("EPSG:4326") if ecu.crs is None else ecu.to_crs("EPSG:4326")
            ecu_main = remove_galapagos(ecu)

            with rasterio.open(tif_path) as src:
                data = src.read(1).astype(np.float32)

                nodata = src.nodata
                if nodata is not None:
                    data[data == nodata] = np.nan

                extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]

                valid = data[~np.isnan(data)]
                vmin, vmax = np.percentile(valid, [2, 98]) if valid.size else (0, 1)

                cmap = plt.get_cmap("terrain").copy()
                cmap.set_bad(alpha=0.0)

                img = self.ax.imshow(
                    data,
                    extent=extent,
                    cmap=cmap,
                    origin="upper",
                    vmin=vmin,
                    vmax=vmax,
                )

            # frontera encima estilo “bonito”
            ecu_main.boundary.plot(ax=self.ax, linewidth=1.8, color="#00E5FF", alpha=0.95)

            self.ax.set_title(f"Mapa de Elevación - {region_name}", color="white", fontsize=16)
            self.ax.set_xlabel("Longitud (Grados)", color="white")
            self.ax.set_ylabel("Latitud (Grados)", color="white")
            self.ax.grid(True, color="gray", linestyle="--", alpha=0.25)

            # Colorbar (una sola)
            if self.colorbar is not None:
                self.colorbar.remove()
                self.colorbar = None
            self.colorbar = self.fig.colorbar(img, ax=self.ax, fraction=0.046, pad=0.04)
            self.colorbar.set_label("Altura [m]", color="white")
            self.colorbar.ax.yaxis.set_tick_params(color="white", labelcolor="white")

            self.canvas.draw_idle()
            self.status_label.configure(text=f"Estado: {region_name} cargado. Puedes seleccionar una zona.")

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al cargar la visualización:\n{e}")
            self.status_label.configure(text="Estado: error al cargar mapa")

    # -----------------------------
    # Toolbar actions
    # -----------------------------
    def _do_zoom(self):
        self.toolbar.zoom()
        self.status_label.configure(text="Estado: modo Zoom activado (toolbar matplotlib).")

    def _do_pan(self):
        self.toolbar.pan()
        self.status_label.configure(text="Estado: modo Pan activado (toolbar matplotlib).")

    # -----------------------------
    # Selection (rectangle)
    # -----------------------------
    def _enable_rect_select(self):
        if self.selector is not None:
            # ya está activo, lo reactivamos
            self.selector.set_active(True)
            self.status_label.configure(text="Estado: selección activa. Arrastra un rectángulo en el mapa.")
            return

        self.status_label.configure(text="Estado: selección activa. Arrastra un rectángulo en el mapa.")

        self.selector = RectangleSelector(
            self.ax,
            self._on_rect_selected,
            useblit=True,
            interactive=True,
            button=[1]
        )
        self.canvas.draw_idle()

    def _on_rect_selected(self, eclick, erelease):
        if eclick.xdata is None or eclick.ydata is None or erelease.xdata is None or erelease.ydata is None:
            return

        lon_min, lon_max = sorted([eclick.xdata, erelease.xdata])
        lat_min, lat_max = sorted([eclick.ydata, erelease.ydata])
        self.current_bbox = (lon_min, lat_min, lon_max, lat_max)

        self._draw_selection_overlay(self.current_bbox)
        self.status_label.configure(text=f"Estado: zona seleccionada {self.current_bbox}")

        # desactivar selector (para que no moleste)
        if self.selector is not None:
            self.selector.set_active(False)

    def _draw_selection_overlay(self, bbox):
        self._clear_selection_overlay()
        lon_min, lat_min, lon_max, lat_max = bbox

        # dibuja un rectángulo sobre el mapa
        rect = plt.Rectangle(
            (lon_min, lat_min),
            lon_max - lon_min,
            lat_max - lat_min,
            fill=False,
            linewidth=2.0,
            edgecolor="#FFCC00"
        )
        self._selection_patch = rect
        self.ax.add_patch(rect)
        self.canvas.draw_idle()

    def _clear_selection_overlay(self):
        if self._selection_patch is not None:
            try:
                self._selection_patch.remove()
            except Exception:
                pass
            self._selection_patch = None

    # -----------------------------
    # Selection (coords dialog)
    # -----------------------------
    def _open_bbox_dialog(self):
        BBoxDialog(self, on_submit=self._set_bbox_from_dialog)

    def _set_bbox_from_dialog(self, bbox):
        self.current_bbox = bbox
        self._draw_selection_overlay(bbox)
        self.status_label.configure(text=f"Estado: zona por coordenadas {self.current_bbox}")

    # -----------------------------
    # Export STL (RAM friendly)
    # -----------------------------
    def _export_selected_zone_stl(self):
        if self.current_bbox is None:
            messagebox.showerror("Error", "Primero selecciona una zona (rectángulo o coordenadas).")
            return

        tif_path = DEFAULT_DEM
        if not os.path.exists(tif_path):
            messagebox.showerror("Error", f"No existe el DEM para exportación:\n{tif_path}")
            return

        try:
            # --- LIMITADOR PROFESIONAL DE RAM ---
            # mientras más grande el recorte, MÁS conviene bajar resolución.
            # 600x600 -> ~718k triángulos (manejable)
            out_h, out_w = 600, 600

            self.status_label.configure(text="Estado: recortando ventana (sin cargar todo el raster)...")
            self.update_idletasks()

            Z, _ = crop_window_from_tif(
                tif_path,
                self.current_bbox,
                out_shape=(out_h, out_w),
                resampling=Resampling.bilinear
            )

            # NaN a 0 para STL (luego si quieres: interpolar huecos)
            Z = np.nan_to_num(Z, nan=0.0)

            self.status_label.configure(text="Estado: creando malla (STL) ...")
            self.update_idletasks()

            exporter = STLExporter(z_scale=1.0, xy_scale=1.0)
            tris = exporter.grid_to_triangles(Z)

            out_dir = os.path.join(ROOT_DIR, "outputs", "stl")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "zona_exportada.stl")

            exporter.write_ascii_stl(tris, out_path, name="ecuador_zone")

            self.status_label.configure(text=f"Estado: STL exportado en {out_path}")
            messagebox.showinfo("OK", f"STL exportado:\n{out_path}")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar STL:\n{e}")
            self.status_label.configure(text="Estado: error exportando STL")


if __name__ == "__main__":
    app = EcuadorMapVisor()
    app.mainloop()
