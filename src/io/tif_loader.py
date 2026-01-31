import os
import numpy as np
import rasterio
from rasterio.windows import from_bounds
import matplotlib.pyplot as plt


class TIFLoader:
    """
    Clase encargada de leer archivos GeoTIFF (.tif) y visualizar la matriz.
    Soporta lectura completa o por ventanas (para evitar llenar RAM).
    """

    def __init__(self, band: int = 1, nodata_to_nan: bool = True):
        self.band = band
        self.nodata_to_nan = nodata_to_nan

    def read_info(self, tif_path: str) -> dict:
        """
        Retorna metadata útil del GeoTIFF.
        """
        if not os.path.exists(tif_path):
            raise FileNotFoundError(f"No se encontró el archivo: {tif_path}")

        with rasterio.open(tif_path) as src:
            return {
                "path": tif_path,
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtype": str(src.dtypes[self.band - 1]),
                "crs": str(src.crs),
                "transform": src.transform,
                "bounds": src.bounds,   # left, bottom, right, top
                "res": src.res,         # (xres, yres)
                "nodata": src.nodata,
            }

    def load_full(self, tif_path: str) -> np.ndarray:
        """
        Lee toda la banda 'band' como matriz NumPy.
        Ojo: si el tif es grande, esto puede consumir RAM.
        """
        if not os.path.exists(tif_path):
            raise FileNotFoundError(f"No se encontró el archivo: {tif_path}")

        with rasterio.open(tif_path) as src:
            arr = src.read(self.band)

            if self.nodata_to_nan and src.nodata is not None:
                # Convertimos a float para poder usar NaN
                arr = arr.astype(np.float32)
                arr[arr == src.nodata] = np.nan

            return arr

    def load_window_bounds(self, tif_path: str, left: float, bottom: float, right: float, top: float) -> np.ndarray:
        """
        Lee solo una ventana definida por coordenadas geográficas (bounds).
        Esto es lo recomendado para trabajar con áreas pequeñas sin reventar RAM.

        Nota: Las coordenadas deben estar en el CRS del tif (en tu caso EPSG:4326 si es lat/lon).
        """
        if not os.path.exists(tif_path):
            raise FileNotFoundError(f"No se encontró el archivo: {tif_path}")

        with rasterio.open(tif_path) as src:
            window = from_bounds(left, bottom, right, top, transform=src.transform)
            arr = src.read(self.band, window=window)

            if self.nodata_to_nan and src.nodata is not None:
                arr = arr.astype(np.float32)
                arr[arr == src.nodata] = np.nan

            return arr

    def show_dem(self, arr, title="DEM"):
        import numpy as np
        import matplotlib.pyplot as plt

        plt.figure()
        valid = arr[~np.isnan(arr)]
        if valid.size == 0:
            raise ValueError("La matriz está vacía (todo NaN).")

        vmin, vmax = np.percentile(valid, [2, 98])
        plt.imshow(arr, vmin=vmin, vmax=vmax)
        plt.title(title)
        plt.axis("off")
        plt.colorbar(label="Elevación (m)")
        plt.show()


    def show_stats(self, arr: np.ndarray) -> dict:
        """
        Retorna stats rápidos para validar datos.
        """
        return {
            "shape": arr.shape,
            "dtype": str(arr.dtype),
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
            "nan_count": int(np.isnan(arr).sum()) if np.issubdtype(arr.dtype, np.floating) else 0,
        }
