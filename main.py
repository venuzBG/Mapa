# # main.py
# import sys
# import os

# # Truco para que Python encuentre tus carpetas src
# sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# # Importaciones desde TUS carpetas
# from src.io.hgt_loader import HGTLoader
# from src.io.display import TerrainDisplay
# from core.terrain_ops import TerrainOperations

# def main():
#     # 1. Configuración
#     archivo = "data/SA17/S01W079.hgt" # Asegúrate de que este archivo exista en tu carpeta data/
    
#     # 2. Instanciar el cargador
#     loader = HGTLoader()
    
#     print(f"Cargando archivo: {archivo}...")
#     raw_map = loader.load_file(archivo)
    
#     if raw_map is not None:
#         # 3. Procesamiento (Usando core)
#         print("Limpiando datos void...")
#         clean_map = TerrainOperations.handle_voids(raw_map)
        
#         # 4. Recorte de prueba (Ej. Cotopaxi suele estar por el centro aprox)
#         print("Recortando zona de interés...")
#         # Nota: Estas coordenadas son ejemplo, tendrás que buscar las exactas
#         mini_map = TerrainOperations.crop_area(clean_map, 400, 400, 300, 300)
        
#         # 5. Visualización (Usando io)
#         print("Generando visualización...")
#         TerrainDisplay.plot_terrain(mini_map, title="Vista Previa Proyecto Mapa 3D")

# if __name__ == "__main__":
#     main()

# import os
# from src.io.tif_loader import TIFLoader
# import rasterio
# import numpy as np



# base_dir = os.path.dirname(__file__)
# tif_path = os.path.join(base_dir, "outputs", "dem", "A17_full.tif")

# loader = TIFLoader()

# info = loader.read_info(tif_path)
# print(info)

# arr = loader.load_full(tif_path)   # OJO: esto carga todo
# print(loader.show_stats(arr))
# loader.show_dem(arr, title="A17_full.tif (DEM)")


# with rasterio.open(tif_path) as src:
#     a = src.read(1)
#     print("raw min/max:", a.min(), a.max())
#     print("nodata:", src.nodata)
#     if src.nodata is not None:
#         print("nodata count:", (a == src.nodata).sum(), "/", a.size)

# with rasterio.open("outputs/dem/A17_full.tif") as src:
#     a = src.read(1)
#     print("raw min/max:", a.min(), a.max())
#     print("nodata count:", (a == src.nodata).sum(), "/", a.size)

# from src.io.tif_loader import TIFLoader
# import os

# base_dir = os.path.dirname(__file__)
# tif_path = os.path.join(base_dir, "outputs", "dem", "ecuador_full.tif")

# loader = TIFLoader()
# arr = loader.load_full(tif_path)
# loader.show_dem(arr, title="ecuador_full.tif (DEM)")

# import os
# import geopandas as gpd
# import rasterio
# import matplotlib.pyplot as plt
# from rasterio.plot import show

# def keep_mainland(geom):
#     # quita Galápagos quedándose con el polígono más grande
#     if geom.geom_type == "MultiPolygon":
#         return max(geom.geoms, key=lambda g: g.area)
#     return geom

# tif_path = os.path.join("outputs", "dem", "ecuador_full.tif")
# geojson_path = os.path.join("data", "ecuador.geojson")  # <-- tu archivo

# # 1) leer frontera desde tu geojson
# ecu = gpd.read_file(geojson_path)

# # 2) asegurar CRS: si no tiene, asumimos EPSG:4326
# if ecu.crs is None:
#     ecu = ecu.set_crs("EPSG:4326")
# else:
#     ecu = ecu.to_crs("EPSG:4326")

# # 3) quitar Galápagos
# ecu["geometry"] = ecu["geometry"].apply(keep_mainland)

# # 4) plot ajustable
# with rasterio.open(tif_path) as src:
#     fig, ax = plt.subplots(constrained_layout=True)
#     show(src, ax=ax)  # DEM

#     ecu.boundary.plot(ax=ax, linewidth=2)

#     # zoom al continente (bounds del polígono)
#     minx, miny, maxx, maxy = ecu.total_bounds
#     padx = (maxx - minx) * 0.15
#     pady = (maxy - miny) * 0.15
#     ax.set_xlim(minx - padx, maxx + padx)
#     ax.set_ylim(miny - pady, maxy + pady)

#     ax.set_title("DEM + frontera de Ecuador (sin Galápagos)")
#     ax.set_xlabel("Longitud")
#     ax.set_ylabel("Latitud")

# plt.show()

import os
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from rasterio.plot import show

def remove_galapagos(ecu_gdf, lon_cutoff=-86.0):
    geoms_out = []

    for geom in ecu_gdf.geometry:
        if geom is None:
            continue

        parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]

        for p in parts:
            if p.centroid.x > lon_cutoff:
                geoms_out.append(p)

    return ecu_gdf.iloc[:0].assign(geometry=geoms_out).set_crs(ecu_gdf.crs)

tif_path = os.path.join("outputs", "dem", "ecuador_full.tif")
geojson_path = os.path.join("data", "ecuador.geojson")

ecu = gpd.read_file(geojson_path)
ecu = ecu.set_crs("EPSG:4326") if ecu.crs is None else ecu.to_crs("EPSG:4326")

ecu_main = remove_galapagos(ecu, lon_cutoff=-86.0)

with rasterio.open(tif_path) as src:
    fig, ax = plt.subplots(constrained_layout=True)
    show(src, ax=ax)

    ecu_main.boundary.plot(ax=ax, linewidth=2)

    # Zoom a continente
    minx, miny, maxx, maxy = ecu_main.total_bounds
    padx = (maxx - minx) * 0.15
    pady = (maxy - miny) * 0.15
    ax.set_xlim(minx - padx, maxx + padx)
    ax.set_ylim(miny - pady, maxy + pady)

    ax.set_title("DEM + frontera de Ecuador (sin Galápagos)")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")

plt.show()
