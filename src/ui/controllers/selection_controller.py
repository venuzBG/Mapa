# src/ui/controllers/selection_controller.py
from matplotlib.widgets import RectangleSelector

class SelectionController:
    def __init__(self, ax, canvas, on_bbox_selected):
        self.ax = ax
        self.canvas = canvas
        self.on_bbox_selected = on_bbox_selected
        self.selector = None

    def enable(self):
        # activa selector
        self.selector = RectangleSelector(
            self.ax,
            self._on_select,
            useblit=True,
            interactive=True,
            button=[1]  # click izquierdo
        )
        self.canvas.draw_idle()

    def disable(self):
        if self.selector:
            self.selector.set_active(False)
            self.selector = None
            self.canvas.draw_idle()

    def _on_select(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        lon_min, lon_max = sorted([x1, x2])
        lat_min, lat_max = sorted([y1, y2])

        bbox = (lon_min, lat_min, lon_max, lat_max)
        self.on_bbox_selected(bbox)
