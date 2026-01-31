import os
import numpy as np
import rasterio
from rasterio.merge import merge

HGT_VOID = -32768

def build_ecuador_full():
    base_dir = os.path.dirname(__file__)
    dem_dir = os.path.join(base_dir, "outputs", "dem")
    out_tif = os.path.join(dem_dir, "ecuador_full.tif")

    tif_files = [
        "A17_full.tif",
        "A18_full.tif",
        "SA17_full.tif",
        "SA18_full.tif",
        "SB17_full.tif",
        "SB18_full.tif",
    ]

    datasets = []
    try:
        for f in tif_files:
            path = os.path.join(dem_dir, f)
            if not os.path.exists(path):
                raise FileNotFoundError(f"No existe: {path}")
            datasets.append(rasterio.open(path))

        # Merge usando NaN para respetar nodata
        mosaic, transform = merge(
            datasets,
            nodata=HGT_VOID,
            res=datasets[0].res
        )

        out = mosaic[0]

        profile = datasets[0].profile.copy()
        profile.update({
            "height": out.shape[0],
            "width": out.shape[1],
            "transform": transform,
            "compress": "LZW",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
            "bigtiff": "IF_SAFER",
        })

        with rasterio.open(out_tif, "w", **profile) as dst:
            dst.write(out, 1)

        print(f"[OK] Ecuador completo creado en:\n{out_tif}")

    finally:
        for ds in datasets:
            ds.close()

if __name__ == "__main__":
    build_ecuador_full()
