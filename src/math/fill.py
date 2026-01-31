import numpy as np

def fill_nans_iterative(z: np.ndarray, iters: int = 6) -> np.ndarray:
    z = z.astype(np.float32).copy()
    for _ in range(iters):
        nan = np.isnan(z)
        if not nan.any():
            break

        up = np.roll(z, -1, axis=0)
        down = np.roll(z, 1, axis=0)
        left = np.roll(z, -1, axis=1)
        right = np.roll(z, 1, axis=1)

        stack = np.stack([up, down, left, right], axis=0)
        mean = np.nanmean(stack, axis=0)
        z[nan] = mean[nan]
    return z
