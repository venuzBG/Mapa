import numpy as np

def linear_scale_to_mm(z_m: np.ndarray, *, zmin_m: float, zmax_m: float, hmax_mm: float) -> np.ndarray:
<<<<<<< HEAD
    z = z_m.astype(np.float32)
    z = np.clip(z, zmin_m, zmax_m)
    denom = (zmax_m - zmin_m) if (zmax_m > zmin_m) else 1.0
    zn = (z - zmin_m) / denom
=======
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
>>>>>>> 36dbaf99186e1fad091bb99e145407ae6b396df9
    return zn * float(hmax_mm)
