import numpy as np
import os

class HGTLoader:
    """
    Clase encargada de la lectura y decodificación de archivos HGT (SRTM).
    """
    
    def __init__(self, size=1201):
        self.size = size  # Estándar SRTM3 es 1201x1201

    def load_file(self, file_path):
        """
        Lee un archivo binario HGT y retorna una matriz NumPy.
        
        Args:
            file_path (str): Ruta al archivo .hgt
            
        Returns:
            np.array: Matriz de (1201, 1201) con las alturas.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

        try:
            # Leemos todo el archivo binario de una sola vez
            # dtype='>i2' es la traducción directa de tu lógica en C:
            # '>' = Big-Endian (Byte A primero)
            # 'i2' = Signed 16-bit integer
            raw_data = np.fromfile(file_path, dtype=np.dtype('>i2'))
            
            # Verificamos integridad de datos
            expected_points = self.size * self.size
            if raw_data.size != expected_points:
                raise ValueError(f"Tamaño incorrecto. Se esperaban {expected_points} puntos, se leyeron {raw_data.size}")

            # Reformateamos el vector plano a una matriz 2D
            elevation_matrix = raw_data.reshape((self.size, self.size))
            
            return elevation_matrix

        except Exception as e:
            print(f"Error crítico leyendo el archivo: {e}")
            return None