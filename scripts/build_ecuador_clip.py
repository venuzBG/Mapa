import os
import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd

def remove_galapagos(gdf, lon_cutoff=-86.0):
    """
    Quito Galápagos filtrando geometrías cuyo centroid esté muy al oeste.
    Ecuador continental queda al este de -86 aprox.
    """
    kept = []
    for geom in gdf.geometry:
        if geom is None:
            continue
        parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in parts:
            if p.centroid.x > lon_cutoff:
                kept.append(p)
    return gdf.iloc[:0].assign(geometry=kept).set_crs(gdf.crs)

def clip_ecuador_display():
    base_dir = os.path.dirname(__file__)
    dem_dir = os.path.join(base_dir, "outputs", "dem")

    in_tif  = os.path.join(dem_dir, "ecuador_display.tif")
    out_tif = os.path.join(dem_dir, "ecuador_display_clipped.tif")

    geojson_path = os.path.join(base_dir, "data", "ecuador.geojson")

    if not os.path.exists(in_tif):
        raise FileNotFoundError(f"No existe: {in_tif}")
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"No existe: {geojson_path}")

    # 1) Leer frontera
    ecu = gpd.read_file(geojson_path)
    ecu = ecu.set_crs("EPSG:4326") if ecu.crs is None else ecu.to_crs("EPSG:4326")

    # 2) Quitar Galápagos
    ecu_main = remove_galapagos(ecu, lon_cutoff=-86.0)

    geoms = list(ecu_main.geometry)

    # 3) Recortar raster con máscara
    with rasterio.open(in_tif) as src:
        out_img, out_transform = mask(
            src,
            geoms,
            crop=True,
            nodata=src.nodata
        )

        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_img.shape[1],
            "width": out_img.shape[2],
            "transform": out_transform,
            "compress": "LZW",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
            "bigtiff": "IF_SAFER",
        })

        with rasterio.open(out_tif, "w", **out_meta) as dst:
            dst.write(out_img)

    print("[OK] Clip creado:", out_tif)

if __name__ == "__main__":
    clip_ecuador_display()
