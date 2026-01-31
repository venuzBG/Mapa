import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window

from src.math.fill import fill_nans_iterative
from src.math.filters import gaussian_smooth_2d
from src.math.scaling import linear_scale_to_mm
from src.core.stl_exporter import export_stl_from_grid

def read_window_downsample(tif_path: str, *, window: Window, out_shape: tuple[int, int]) -> np.ndarray:
    """Lee solo una ventana del GeoTIFF y la reduce con bilinear."""
    with rasterio.open(tif_path) as src:
        arr = src.read(
            1,
            window=window,
            out_shape=out_shape,
            resampling=Resampling.bilinear
        ).astype(np.float32)

        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan

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
        zmin_m=zmin_m,
        zmax_m=zmax_m,
        hmax_mm=hmax_mm
    )
    export_stl_from_grid(dem_mm, out_path=stl_path, dx_mm=dx_mm, dy_mm=dy_mm)
