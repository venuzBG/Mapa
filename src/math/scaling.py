import numpy as np

def linear_scale_to_mm(z_m: np.ndarray, *, zmin_m: float, zmax_m: float, hmax_mm: float) -> np.ndarray:
    z = z_m.astype(np.float32)
    z = np.clip(z, zmin_m, zmax_m)
    denom = (zmax_m - zmin_m) if (zmax_m > zmin_m) else 1.0
    zn = (z - zmin_m) / denom
    return zn * float(hmax_mm)
