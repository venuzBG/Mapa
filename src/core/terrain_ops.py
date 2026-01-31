import numpy as np

class TerrainOperations:

    @staticmethod
    def handle_voids(matrix, fill_value=None):
        VOID_VALUE = -32768
        if fill_value is None:
            valid_mask = matrix != VOID_VALUE
            if np.any(valid_mask):
                fill_value = matrix[valid_mask].min()
            else:
                fill_value = 0 # Valor por defecto si todo es error

        matrix[matrix == VOID_VALUE] = fill_value
        return matrix

    @staticmethod
    def crop_area(matrix, x_start, y_start, width, height):
        # Verificamos que no nos salgamos de los límites
        max_y, max_x = matrix.shape
        if x_start + width > max_x or y_start + height > max_y:
            raise ValueError("El recorte excede el tamaño del mapa")

        return matrix[y_start : y_start + height, x_start : x_start + width]