import rasterio
from rasterio.windows import Window
from rasterio.transform import rowcol

def bbox_to_window(src: rasterio.DatasetReader, *, left, bottom, right, top) -> Window:
    """
    Convierte un bbox (lon/lat en EPSG del raster) a Window.
    """
    # rowcol recibe (x, y)
    r0, c0 = rowcol(src.transform, left, top)      # esquina superior-izq
    r1, c1 = rowcol(src.transform, right, bottom)  # esquina inferior-der

    # Asegurar orden
    row_start, row_stop = sorted([r0, r1])
    col_start, col_stop = sorted([c0, c1])

    # Clamp a límites
    row_start = max(0, row_start)
    col_start = max(0, col_start)
    row_stop = min(src.height, row_stop)
    col_stop = min(src.width, col_stop)

    height = max(1, row_stop - row_start)
    width = max(1, col_stop - col_start)

    return Window(col_start, row_start, width, height)

def window_bounds(src: rasterio.DatasetReader, win: Window):
    """Devuelve bounds (left, bottom, right, top) del Window."""
    return rasterio.windows.bounds(win, src.transform)
