import os
import re
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.merge import merge
from rasterio.transform import from_origin


HGT_VOID = -32768  # nodata típico en SRTM/HGT


def parse_hgt_name(filename: str) -> tuple[float, float]:
    """
    Parsea nombres tipo N00W079.hgt -> (lat, lon) en grados enteros del SW corner.
    Para HGT: el tile cubre [lat, lat+1] y [lon, lon+1]
    """
    m = re.match(r"^([NS])(\d{2})([EW])(\d{3})\.hgt$", filename, re.IGNORECASE)
    if not m:
        raise ValueError(f"Nombre HGT inválido: {filename}")

    ns, lat_s, ew, lon_s = m.groups()
    lat = int(lat_s)
    lon = int(lon_s)

    if ns.upper() == "S":
        lat = -lat
    if ew.upper() == "W":
        lon = -lon

    return float(lat), float(lon)


def read_hgt_array(path: str, size: int = 1201) -> np.ndarray:
    """
    Lee HGT como int16 (big-endian). Devuelve matriz (size, size).
    """
    raw = np.fromfile(path, dtype=np.dtype(">i2"))
    expected = size * size
    if raw.size != expected:
        raise ValueError(f"{os.path.basename(path)} tamaño incorrecto: {raw.size} != {expected}")
    return raw.reshape((size, size))


def hgt_to_mem_dataset(hgt_path: str, size: int = 1201) -> tuple[MemoryFile, rasterio.DatasetReader]:
    name = os.path.basename(hgt_path)
    lat, lon = parse_hgt_name(name)

    px = 1.0 / (size - 1)
    transform = from_origin(lon, lat + 1.0, px, px)

    arr = read_hgt_array(hgt_path, size=size).astype(np.float32)
    arr[arr == HGT_VOID] = np.nan

    profile = {
        "driver": "GTiff",
        "height": size,
        "width": size,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": np.nan,
    }

    mem = MemoryFile()
    ds = mem.open(**profile)
    ds.write(arr, 1)
    return mem, ds


def build_zone_mosaic(zone_dir: str, out_tif: str, size: int = 1201) -> str:
    """
    Une todos los .hgt de una carpeta (ej. data/A17) y crea un GeoTIFF full resolución.
    - Lee HGT -> float32 con NaN en voids
    - merge() con NaN
    - guarda como int16 restaurando nodata=-32768
    """
    zone_dir = os.path.abspath(zone_dir)
    os.makedirs(os.path.dirname(out_tif), exist_ok=True)

    hgt_files = sorted([f for f in os.listdir(zone_dir) if f.lower().endswith(".hgt")])
    if not hgt_files:
        raise FileNotFoundError(f"No hay .hgt en: {zone_dir}")

    memfiles: list[MemoryFile] = []
    datasets: list[rasterio.DatasetReader] = []

    try:
        # 1) Abrir cada HGT como dataset georreferenciado en memoria
        for f in hgt_files:
            path = os.path.join(zone_dir, f)
            mem, ds = hgt_to_mem_dataset(path, size=size)
            memfiles.append(mem)
            datasets.append(ds)

        # 2) Merge usando NaN como nodata
        mosaic, out_transform = merge(datasets, nodata=np.nan, res=datasets[0].res)

        # 3) Convertir a int16 restaurando nodata
        out = mosaic[0]  # (H, W) float32
        out_int16 = np.where(np.isnan(out), HGT_VOID, np.rint(out)).astype(np.int16)

        # 4) Perfil de salida correcto (int16 + nodata=-32768)
        out_profile = datasets[0].profile.copy()
        out_profile.update({
            "dtype": "int16",
            "nodata": HGT_VOID,
            "height": out_int16.shape[0],
            "width": out_int16.shape[1],
            "transform": out_transform,
            "compress": "LZW",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
            "bigtiff": "IF_SAFER",
        })

        # 5) Escribir al TIFF
        with rasterio.open(out_tif, "w", **out_profile) as dst:
            dst.write(out_int16, 1)

        return out_tif

    finally:
        for ds in datasets:
            ds.close()
        for mem in memfiles:
            mem.close()
