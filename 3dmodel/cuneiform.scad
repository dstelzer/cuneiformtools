module wedge(x, y, z, w, h, phi){
	s = w / sqrt(2);
	l = sqrt(h*h - s*s - s*s);
	theta = atan((w/2)/l);

	translate([x, y, z])
	rotate([0, 0, phi])
	rotate([0, -theta, 0])
	rotate([45, 0, 0])
	translate([0, -s/2, -s/2])
	cube([l, s, s]);
}

module haken(x, y, z, s, d){
	w = s*sqrt(2);
	theta = atan(d/(w/2));
	translate([x, y, z])
	rotate([0, -theta, 0])
	translate([0, 0, -d])
	rotate([0, 0, -45])
	cube([s, s, d]);
}