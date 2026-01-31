import numpy as np

def export_stl_from_grid(z_mm: np.ndarray, *, out_path: str, dx_mm: float = 1.0, dy_mm: float = 1.0):
    """
    Convierte grilla regular z_mm a STL (triángulos).
    OJO: si la matriz es grande, explota. Por eso antes hay que downsample.
    """
    z = z_mm.astype(np.float32)
    h, w = z.shape

    # Reemplazar NaN por 0 (o podrías recortar donde hay NaN)
    z = np.nan_to_num(z, nan=0.0)

    def v(i, j):
        return np.array([j * dx_mm, i * dy_mm, z[i, j]], dtype=np.float32)

    tris = []
    for i in range(h - 1):
        for j in range(w - 1):
            p00 = v(i, j)
            p01 = v(i, j + 1)
            p10 = v(i + 1, j)
            p11 = v(i + 1, j + 1)

            # dos triángulos por celda
            tris.append((p00, p10, p11))
            tris.append((p00, p11, p01))

    # Guardar STL ASCII simple
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("solid dem\n")
        for a, b, c in tris:
            n = np.cross(b - a, c - a)
            norm = np.linalg.norm(n)
            if norm > 0:
                n = n / norm
            else:
                n = np.array([0, 0, 1], dtype=np.float32)

            f.write(f"  facet normal {n[0]} {n[1]} {n[2]}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {a[0]} {a[1]} {a[2]}\n")
            f.write(f"      vertex {b[0]} {b[1]} {b[2]}\n")
            f.write(f"      vertex {c[0]} {c[1]} {c[2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid dem\n")
