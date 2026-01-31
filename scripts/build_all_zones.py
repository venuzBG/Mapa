import os
import traceback
from src.core.zone_builder import build_zone_mosaic

def main():
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")
    out_dir  = os.path.join(base_dir, "outputs", "dem")
    os.makedirs(out_dir, exist_ok=True)

    zones = ["A17", "A18", "SA17", "SA18", "SB17", "SB18"]

    print("[INFO] data_dir:", data_dir)
    print("[INFO] out_dir :", out_dir)

    for z in zones:
        zone_path = os.path.join(data_dir, z)
        out_tif = os.path.join(out_dir, f"{z}_full.tif")

        print(f"\n===== ZONA {z} =====")
        if not os.path.isdir(zone_path):
            print(f"[SKIP] No existe carpeta: {zone_path}")
            continue

        hgts = sorted([f for f in os.listdir(zone_path) if f.lower().endswith(".hgt")])
        print(f"[INFO] Encontrados {len(hgts)} .hgt en {zone_path}")

        # Muestra 3 nombres para detectar si hay formato raro
        for f in hgts[:3]:
            print("  -", f)

        try:
            result = build_zone_mosaic(zone_path, out_tif, size=1201)
            print(f"[OK] Creado: {result}")
            print(f"[OK] bytes: {os.path.getsize(result)}")
        except Exception:
            print(f"[ERROR] Falló la zona {z}. Razón:")
            traceback.print_exc()
            # sigue con la siguiente zona
            continue

if __name__ == "__main__":
    main()
