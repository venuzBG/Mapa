import numpy as np
import geopandas as gpd
from rasterio.features import geometry_mask

from src.io.geojson_utils import keep_mainland

def load_ecuador_geometry(geojson_path: str, target_crs: str):
    gdf = gpd.read_file(geojson_path)
    # si tu geojson tiene varios features, nos quedamos con todos y unimos
    gdf = gdf.to_crs(target_crs)
    geom = gdf.unary_union
    geom = keep_mainland(geom)  # quitar Galápagos
    return geom

def mask_array_to_geometry(arr: np.ndarray, *, transform, geometry, nodata_value=np.nan):
    """
    Crea máscara booleana a partir de geometry y la aplica al array.
    True = se enmascara (se pone nodata)
    """
    m = geometry_mask(
        [geometry],
        out_shape=arr.shape,
        transform=transform,
        invert=True  # True dentro del polígono
    )
    out = arr.copy()
    out[~m] = nodata_value
    return out
