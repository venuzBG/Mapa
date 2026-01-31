# src/processing/raster_cropper.py
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling

class RasterCropper:
    def __init__(self, tif_path: str):
        self.tif_path = tif_path

    def crop_window(self, bbox, out_shape=None, resampling=Resampling.bilinear):
        """
        bbox = (lon_min, lat_min, lon_max, lat_max)
        out_shape = (h, w) opcional -> reduce resolución sin cargar todo
        """
        lon_min, lat_min, lon_max, lat_max = bbox

        with rasterio.open(self.tif_path) as src:
            window = from_bounds(lon_min, lat_min, lon_max, lat_max, transform=src.transform)
            window = window.round_offsets().round_lengths()

            if out_shape is None:
                arr = src.read(1, window=window)
                transform = src.window_transform(window)
            else:
                # lee ya re-muestreado (mucho menos RAM)
                arr = src.read(
                    1,
                    window=window,
                    out_shape=out_shape,
                    resampling=resampling
                )
                # ajustar transform al nuevo tamaño
                transform = src.window_transform(window)
                scale_x = (window.width / out_shape[1])
                scale_y = (window.height / out_shape[0])
                transform = transform * rasterio.Affine.scale(scale_x, scale_y)

            nodata = src.nodata

        arr = arr.astype(np.float32)
        if nodata is not None:
            arr[arr == nodata] = np.nan

        return arr, transform
