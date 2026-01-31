import numpy as np

<<<<<<< HEAD
def export_stl_from_grid(
    z_mm: np.ndarray,
    *,
    out_path: str,
    dx_mm: float = 1.0,
    dy_mm: float = 1.0,
    base_thickness_mm: float = 1.5
):
    """
    STL ASCII:
    - Superficie arriba
    - Base plana abajo (base_thickness_mm)
    """
    z = np.nan_to_num(z_mm.astype(np.float32), nan=0.0)
    h, w = z.shape

    z_top = z + base_thickness_mm
    z_bot = np.zeros_like(z_top, dtype=np.float32)

    def v(i, j, zz):
        return np.array([j * dx_mm, i * dy_mm, zz[i, j]], dtype=np.float32)

    tris = []

    # Superficie (top)
    for i in range(h - 1):
        for j in range(w - 1):
            p00 = v(i, j, z_top)
            p01 = v(i, j + 1, z_top)
            p10 = v(i + 1, j, z_top)
            p11 = v(i + 1, j + 1, z_top)
            tris.append((p00, p10, p11))
            tris.append((p00, p11, p01))

    # Base (bottom) invertida
    for i in range(h - 1):
        for j in range(w - 1):
            p00 = v(i, j, z_bot)
            p01 = v(i, j + 1, z_bot)
            p10 = v(i + 1, j, z_bot)
            p11 = v(i + 1, j + 1, z_bot)
            tris.append((p00, p11, p10))
            tris.append((p00, p01, p11))

    # Paredes laterales (borde)
    def add_wall(edge_points_top, edge_points_bot):
        for (a1, a2), (b1, b2) in zip(edge_points_top, edge_points_bot):
            tris.append((a1, b2, b1))
            tris.append((a1, a2, b2))

    # construir bordes
    top_left = [(v(i, 0, z_top), v(i+1, 0, z_top)) for i in range(h-1)]
    bot_left = [(v(i, 0, z_bot), v(i+1, 0, z_bot)) for i in range(h-1)]
    add_wall(top_left, bot_left)

    top_right = [(v(i, w-1, z_top), v(i+1, w-1, z_top)) for i in range(h-1)]
    bot_right = [(v(i, w-1, z_bot), v(i+1, w-1, z_bot)) for i in range(h-1)]
    add_wall(top_right, bot_right)

    top_top = [(v(0, j, z_top), v(0, j+1, z_top)) for j in range(w-1)]
    bot_top = [(v(0, j, z_bot), v(0, j+1, z_bot)) for j in range(w-1)]
    add_wall(top_top, bot_top)

    top_bottom = [(v(h-1, j, z_top), v(h-1, j+1, z_top)) for j in range(w-1)]
    bot_bottom = [(v(h-1, j, z_bot), v(h-1, j+1, z_bot)) for j in range(w-1)]
    add_wall(top_bottom, bot_bottom)

    # Guardar STL
=======
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
>>>>>>> 36dbaf99186e1fad091bb99e145407ae6b396df9
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("solid dem\n")
        for a, b, c in tris:
            n = np.cross(b - a, c - a)
            norm = np.linalg.norm(n)
<<<<<<< HEAD
            n = (n / norm) if norm > 0 else np.array([0, 0, 1], dtype=np.float32)
=======
            if norm > 0:
                n = n / norm
            else:
                n = np.array([0, 0, 1], dtype=np.float32)
>>>>>>> 36dbaf99186e1fad091bb99e145407ae6b396df9

            f.write(f"  facet normal {n[0]} {n[1]} {n[2]}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {a[0]} {a[1]} {a[2]}\n")
            f.write(f"      vertex {b[0]} {b[1]} {b[2]}\n")
            f.write(f"      vertex {c[0]} {c[1]} {c[2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid dem\n")
