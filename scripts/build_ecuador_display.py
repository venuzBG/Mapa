import os
import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.warp import reproject

def build_ecuador_display(scale: int = 8):
    """
    Crea un GeoTIFF reducido para visualización (GUI) usando interpolación bilineal.
    - NO reemplaza ecuador_full.tif
    - Genera ecuador_display.tif (mucho más ligero)
    """
    base_dir = os.path.dirname(__file__)
    dem_dir = os.path.join(base_dir, "outputs", "dem")

    in_tif = os.path.join(dem_dir, "ecuador_full.tif")
    out_tif = os.path.join(dem_dir, "ecuador_display.tif")

    if not os.path.exists(in_tif):
        raise FileNotFoundError(f"No existe: {in_tif}")

    with rasterio.open(in_tif) as src:
        # Nuevo tamaño (reducido)
        new_width = max(1, src.width // scale)
        new_height = max(1, src.height // scale)

        # Transform ajustado
        scale_x = src.width / new_width
        scale_y = src.height / new_height
        new_transform = src.transform * Affine.scale(scale_x, scale_y)

        # Destination array
        dst = np.empty((new_height, new_width), dtype=np.float32)

        # Reproject (maneja nodata correctamente) con bilinear
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=new_transform,
            dst_crs=src.crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=src.nodata,
        )

        # Volver a int16 (como el DEM original)
        if src.dtypes[0] == "int16":
            dst_out = np.rint(dst).astype(np.int16)
        else:
            dst_out = dst.astype(src.dtypes[0])

        profile = src.profile.copy()
        profile.update({
            "height": new_height,
            "width": new_width,
            "transform": new_transform,
            "compress": "LZW",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
            "bigtiff": "IF_SAFER",
        })

        with rasterio.open(out_tif, "w", **profile) as out:
            out.write(dst_out, 1)

            # Overviews (piramides) para zoom/pan rápido en GUI
            factors = [2, 4, 8, 16]
            out.build_overviews(factors, Resampling.average)
            out.update_tags(ns="rio_overview", resampling="average")

    print(f"[OK] Archivo liviano creado:\n{out_tif}")
    print(f"     Escala: 1/{scale} -> {new_width}x{new_height}")

if __name__ == "__main__":
    build_ecuador_display(scale=8)
