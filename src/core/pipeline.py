import numpy as np
import rasterio
from rasterio.enums import Resampling
<<<<<<< HEAD

from src.io.window_utils import bbox_to_window
from src.io.masker import load_ecuador_geometry, mask_array_to_geometry
=======
from rasterio.windows import Window

>>>>>>> 36dbaf99186e1fad091bb99e145407ae6b396df9
from src.math.fill import fill_nans_iterative
from src.math.filters import gaussian_smooth_2d
from src.math.scaling import linear_scale_to_mm
from src.core.stl_exporter import export_stl_from_grid

<<<<<<< HEAD
HGT_VOID = -32768

def read_bbox_downsample(tif_path: str, *, bbox, out_shape):
    """
    Lee solo bbox (lon/lat) del tif y reduce a out_shape con bilinear.
    Retorna (arr_m, transform_window, crs)
    """
    left, bottom, right, top = bbox

    with rasterio.open(tif_path) as src:
        win = bbox_to_window(src, left=left, bottom=bottom, right=right, top=top)
        transform = rasterio.windows.transform(win, src.transform)

        arr = src.read(
            1,
            window=win,
=======
def read_window_downsample(tif_path: str, *, window: Window, out_shape: tuple[int, int]) -> np.ndarray:
    """Lee solo una ventana del GeoTIFF y la reduce con bilinear."""
    with rasterio.open(tif_path) as src:
        arr = src.read(
            1,
            window=window,
>>>>>>> 36dbaf99186e1fad091bb99e145407ae6b396df9
            out_shape=out_shape,
            resampling=Resampling.bilinear
        ).astype(np.float32)

        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan

<<<<<<< HEAD
        # También por si está como HGT_VOID
        arr[arr == HGT_VOID] = np.nan

        return arr, transform, src.crs

def prepare_for_3d(
    arr_m: np.ndarray,
    *,
    fill_iters=6,
    gauss_sigma=2.0,
    zmin_m=0.0,
    zmax_m=6000.0,
    hmax_mm=12.0
):
    z = fill_nans_iterative(arr_m, iters=fill_iters)
    z = gaussian_smooth_2d(z, sigma=gauss_sigma)
    z_mm = linear_scale_to_mm(z, zmin_m=zmin_m, zmax_m=zmax_m, hmax_mm=hmax_mm)
    return z_mm

def export_bbox_to_stl(
    *,
    tif_path: str,
    geojson_path: str,
    bbox,
    out_shape=(600, 600),
    stl_path="outputs/stl/selection.stl",
    gauss_sigma=2.0,
    zmin_m=0.0,
    zmax_m=6000.0,
    hmax_mm=12.0,
    dx_mm=1.0,
    dy_mm=1.0,
    base_thickness_mm=1.5
):
    # 1) leer bbox reducido
    arr, transform, crs = read_bbox_downsample(tif_path, bbox=bbox, out_shape=out_shape)

    # 2) máscara Ecuador (sin Galápagos) dentro de esa ventana
    geom = load_ecuador_geometry(geojson_path, target_crs=str(crs))
    arr = mask_array_to_geometry(arr, transform=transform, geometry=geom, nodata_value=np.nan)

    # 3) métodos numéricos: fill + gauss + escala
    z_mm = prepare_for_3d(
        arr,
        fill_iters=6,
        gauss_sigma=gauss_sigma,
=======
    return arr

def prepare_dem_for_3d(
    dem_m: np.ndarray,
    *,
    fill_iters: int = 6,
    gaussian_sigma: float = 2.0,
    zmin_m: float = 0.0,
    zmax_m: float = 6000.0,
    hmax_mm: float = 12.0
) -> np.ndarray:
    """Aplica: fill NaNs -> gauss -> escala a mm."""
    z = dem_m.copy()

    # 1) rellenar huecos pequeños
    z = fill_nans_iterative(z, iters=fill_iters)

    # 2) suavizar
    z = gaussian_smooth_2d(z, sigma=gaussian_sigma)

    # 3) escalar a mm
    z_mm = linear_scale_to_mm(z, zmin_m=zmin_m, zmax_m=zmax_m, hmax_mm=hmax_mm)
    return z_mm

def export_selection_to_stl(
    *,
    tif_path: str,
    window: Window,
    out_shape: tuple[int, int],
    stl_path: str,
    gaussian_sigma: float = 2.0,
    zmin_m: float = 0.0,
    zmax_m: float = 6000.0,
    hmax_mm: float = 12.0,
    dx_mm: float = 1.0,
    dy_mm: float = 1.0
):
    dem_m = read_window_downsample(tif_path, window=window, out_shape=out_shape)
    dem_mm = prepare_dem_for_3d(
        dem_m,
        gaussian_sigma=gaussian_sigma,
>>>>>>> 36dbaf99186e1fad091bb99e145407ae6b396df9
        zmin_m=zmin_m,
        zmax_m=zmax_m,
        hmax_mm=hmax_mm
    )
<<<<<<< HEAD

    # 4) STL
    export_stl_from_grid(
        z_mm,
        out_path=stl_path,
        dx_mm=dx_mm,
        dy_mm=dy_mm,
        base_thickness_mm=base_thickness_mm
    )

    return stl_path
=======
    export_stl_from_grid(dem_mm, out_path=stl_path, dx_mm=dx_mm, dy_mm=dy_mm)
>>>>>>> 36dbaf99186e1fad091bb99e145407ae6b396df9
