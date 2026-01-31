import numpy as np

def linear_scale_to_mm(z_m: np.ndarray, *, zmin_m: float, zmax_m: float, hmax_mm: float) -> np.ndarray:
    """
    Escala linealmente elevaciones en metros (z_m) al rango [0, hmax_mm] en milímetros.

    zmin_m y zmax_m: dominio de elevación que quieres mapear (p.ej. 0..6000)
    """
    z = z_m.astype(np.float32)

    # Recortar al rango para evitar valores raros
    z = np.clip(z, zmin_m, zmax_m)

    # Normalización 0..1
    denom = (zmax_m - zmin_m) if (zmax_m > zmin_m) else 1.0
    zn = (z - zmin_m) / denom

    # Escala a mm
    return zn * float(hmax_mm)
