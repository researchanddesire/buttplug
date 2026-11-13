"""Exact volume intersections between saved native component solids.

Decompose compounds before the kernel operation so a PCB's many package
solids are not unnecessarily checked against each other. Every surviving
pair still uses the native BRep Boolean; positive pieces are fused to avoid
double-counting overlapping solids. No geometry error is suppressed.
"""
import Part


def solid_parts(shape):
    return [(solid, solid.optimalBoundingBox(False, False))
            for solid in shape.Solids]


def exact_common(first, second):
    """Return the union of all actual solid/solid volume intersections."""
    pieces = []
    for a, a_bounds in first:
        for b, b_bounds in second:
            if not a_bounds.intersect(b_bounds):
                continue
            if any(min(getattr(a_bounds,axis+'Max'),getattr(b_bounds,axis+'Max'))
                   <= max(getattr(a_bounds,axis+'Min'),getattr(b_bounds,axis+'Min'))
                   for axis in ('X','Y','Z')):
                continue  # Boundary-only bounding-box contact has no volume.
            common = a.common(b)
            if common.Volume > 0:
                pieces.append(common)
    if not pieces:
        return Part.makeCompound([])
    result = pieces[0]
    for piece in pieces[1:]:
        result = result.fuse(piece)
    return result
