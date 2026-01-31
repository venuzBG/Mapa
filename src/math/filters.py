import numpy as np

def gaussian_kernel_1d(sigma: float, radius: int | None = None) -> np.ndarray:
    if radius is None:
        radius = int(max(1, round(3 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float32)
    k = np.exp(-(x * x) / (2 * sigma * sigma))
    k /= np.sum(k)
    return k

def gaussian_smooth_2d(z: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """
    Suavizado gaussiano separable (1D en X y luego en Y).
    Mantiene NaN como NaN.
    """
    z = z.astype(np.float32)

    # máscara de válidos
    valid = ~np.isnan(z)
    if valid.sum() == 0:
        return z

    k = gaussian_kernel_1d(sigma)

    # Convolución 1D por filas
    def convolve_1d(arr: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        pad = len(kernel) // 2
        arr_p = np.pad(arr, (pad, pad), mode="edge")
        out = np.zeros_like(arr, dtype=np.float32)
        for i in range(arr.size):
            out[i] = np.sum(arr_p[i:i+len(kernel)] * kernel)
        return out

    # Aplicar con “normalización” para no afectar NaN
    z0 = np.where(valid, z, 0.0).astype(np.float32)
    w0 = valid.astype(np.float32)

    # filas
    z1 = np.vstack([convolve_1d(z0[r, :], k) for r in range(z0.shape[0])])
    w1 = np.vstack([convolve_1d(w0[r, :], k) for r in range(w0.shape[0])])

    # columnas
    z2 = np.vstack([convolve_1d(z1[:, c], k) for c in range(z1.shape[1])]).T
    w2 = np.vstack([convolve_1d(w1[:, c], k) for c in range(w1.shape[1])]).T

    out = z2 / np.maximum(w2, 1e-6)
    out[~valid] = np.nan
    return out
