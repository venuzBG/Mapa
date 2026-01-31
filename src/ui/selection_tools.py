from dataclasses import dataclass
from matplotlib.widgets import RectangleSelector

@dataclass
class SelectionBBox:
    left: float
    bottom: float
    right: float
    top: float

class MapSelectionController:
    """
    Maneja selección rectangular sobre un Axes (matplotlib) y devuelve bbox lon/lat.
    """
    def __init__(self, ax, on_select_callback):
        self.ax = ax
        self.on_select_callback = on_select_callback
        self.rs = None

    def enable(self):
        if self.rs is not None:
            return

        def onselect(eclick, erelease):
            x1, y1 = eclick.xdata, eclick.ydata
            x2, y2 = erelease.xdata, erelease.ydata
            if x1 is None or x2 is None or y1 is None or y2 is None:
                return
            left, right = sorted([x1, x2])
            bottom, top = sorted([y1, y2])
            self.on_select_callback(SelectionBBox(left, bottom, right, top))

        self.rs = RectangleSelector(
            self.ax,
            onselect,
            useblit=True,
            interactive=True,
            button=[1],  # click izq
        )

    def disable(self):
        if self.rs is None:
            return
        self.rs.set_active(False)
        self.rs = None
