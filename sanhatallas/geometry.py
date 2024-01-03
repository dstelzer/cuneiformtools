from collections import namedtuple
from math import sin, cos

XY = namedtuple('XY', 'x y')

def sgn(x): # Python doesn't have a signum function; this could probably be made more efficient
	if x == 0: return 0
	elif x < 0: return -1
	else: return 1
# Use a matrix determinant to decide if three points are clockwise or counterclockwise
# See http://www.cs.cmu.edu/~quake/robust.html
def winding(a, b, c): return sgn((a.x-c.x)*(b.y-c.y) - (a.y-c.y)*(b.x-c.x))
# Points A and B are separated by segment CD iff CDA and CDB have opposite windings
def separates(a, b, c, d): return winding(c, d, a) != winding(c, d, b)
# Finally, segments AB and CD intersect iff A and B are separated by CD, and C and D are separated by AB
# See https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
def intersects(a, b, c, d): return separates(a, b, c, d) and separates(c, d, a, b)

def rotate(a, theta): return XY(a.x*cos(theta)-a.y*sin(theta), a.x*sin(theta)+a.y*cos(theta)) # Just apply the two-dimensional rotation matrix "longhand" instead of involving matrix multiplication
