# src/processing/mesh_exporter.py
import numpy as np

class STLExporter:
    def __init__(self, z_scale=1.0, xy_scale=1.0):
        """
        z_scale: factor vertical (exageración)
        xy_scale: escala horizontal (si quieres mm/metros luego)
        """
        self.z_scale = z_scale
        self.xy_scale = xy_scale

    def grid_to_triangles(self, Z: np.ndarray):
        """
        Convierte una matriz Z (h,w) a triángulos (solo superficie).
        Devuelve lista de triángulos, cada triángulo = (v1,v2,v3) con v=(x,y,z).
        """
        h, w = Z.shape
        tris = []

        for i in range(h - 1):
            for j in range(w - 1):
                z00 = Z[i, j]
                z10 = Z[i+1, j]
                z01 = Z[i, j+1]
                z11 = Z[i+1, j+1]

                # si hay NaN en esta celda, saltar (evita huecos)
                if np.isnan([z00, z10, z01, z11]).any():
                    continue

                # coordenadas en grid (puedes mapear a metros después)
                x0, x1 = j * self.xy_scale, (j+1) * self.xy_scale
                y0, y1 = i * self.xy_scale, (i+1) * self.xy_scale

                z00 *= self.z_scale
                z10 *= self.z_scale
                z01 *= self.z_scale
                z11 *= self.z_scale

                # dos triángulos por celda
                v00 = (x0, y0, z00)
                v10 = (x0, y1, z10)
                v01 = (x1, y0, z01)
                v11 = (x1, y1, z11)

                tris.append((v00, v10, v01))
                tris.append((v10, v11, v01))

        return tris

    def write_ascii_stl(self, triangles, out_path: str, name="terrain"):
        def normal(v1, v2, v3):
            a = np.array(v2) - np.array(v1)
            b = np.array(v3) - np.array(v1)
            n = np.cross(a, b)
            norm = np.linalg.norm(n)
            return (n / norm) if norm != 0 else np.array([0.0, 0.0, 0.0])

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"solid {name}\n")
            for v1, v2, v3 in triangles:
                n = normal(v1, v2, v3)
                f.write(f"  facet normal {n[0]} {n[1]} {n[2]}\n")
                f.write("    outer loop\n")
                f.write(f"      vertex {v1[0]} {v1[1]} {v1[2]}\n")
                f.write(f"      vertex {v2[0]} {v2[1]} {v2[2]}\n")
                f.write(f"      vertex {v3[0]} {v3[1]} {v3[2]}\n")
                f.write("    endloop\n")
                f.write("  endfacet\n")
            f.write(f"endsolid {name}\n")
