# src/ui/layers.py
import geopandas as gpd

class LayerManager:
    def __init__(self, border_path: str, cantons_path: str | None = None):
        self.border_path = border_path
        self.cantons_path = cantons_path

        self._border_geom = None
        self._cantons_gdf = None

    def load(self):
        # Borde Ecuador
        border_gdf = gpd.read_file(self.border_path).to_crs("EPSG:4326")
        geom = border_gdf.unary_union

        # Quedarse con polígono más grande (sin Galápagos)
        if geom.geom_type == "MultiPolygon":
            geom = max(list(geom.geoms), key=lambda g: g.area)

        self._border_geom = geom

        # Cantones (opcional)
        if self.cantons_path:
            self._cantons_gdf = gpd.read_file(self.cantons_path).to_crs("EPSG:4326")

    @property
    def border_geom(self):
        return self._border_geom

    def plot_border(self, ax):
        gpd.GeoSeries([self._border_geom], crs="EPSG:4326").boundary.plot(
            ax=ax, linewidth=1.8, color="#00E5FF", zorder=10
        )

    def plot_cantons(self, ax):
        if self._cantons_gdf is None:
            return

        # Si es pesado, puedes simplificar un poquito:
        # self._cantons_gdf["geometry"] = self._cantons_gdf["geometry"].simplify(0.001)

        self._cantons_gdf.boundary.plot(
            ax=ax, linewidth=0.6, color="#00E5FF", alpha=0.75, zorder=9
        )

