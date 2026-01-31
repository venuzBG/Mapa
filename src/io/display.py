import matplotlib.pyplot as plt

class TerrainDisplay:
    @staticmethod
    def plot_terrain(matrix, title="Mapa de Elevación"):
        plt.figure(figsize=(10, 8))
        plt.imshow(matrix, cmap='terrain')
        plt.colorbar(label='Altura (m)')
        plt.title(title)
        plt.show()