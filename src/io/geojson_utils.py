from shapely.geometry import MultiPolygon, Polygon

def keep_mainland(geom):
    """
    Si Ecuador viene como MultiPolygon, retorna el polígono de mayor área (continental).
    """
    if geom is None:
        return geom
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        return max(list(geom.geoms), key=lambda g: g.area)
    return geom
