from collections import namedtuple

XY = namedtuple('XY', 'x y')

# Use a matrix determinant to decide if three points are clockwise or counterclockwise
# See http://www.cs.cmu.edu/~quake/robust.html
def winding(a, b, c): return (a.x-c.x)*(b.y-c.y) - (a.y-c.y)*(b.x-c.x)
# Points A and B are separated by segment CD iff CDA and CDB have opposite windings
def separates(a, b, c, d): return winding(c, d, a) != winding(c, d, b)
# Finally, segments AB and CD intersect iff A and B are separated by CD, and C and D are separated by AB
# See https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
def intersects(a, b, c, d): return separates(a, b, c, d) and separates(c, d, a, b)
