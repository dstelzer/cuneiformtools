MAX_STROKE_WIDTH = 1/5;

module wedge(x, y, z, w, h, phi, o=false){
	// o is for offset, an experiment with moving the stroke so that its greatest depth would be at the origin point
	// It's not working very well; just don't use it for now
	// Also need to extend the stroke by delta if we do that
	
	s = w / sqrt(2);
	d = w / 2; // Depth of stroke, from head to deepest point
	l = sqrt(h*h - d*d); // Length of stroke, from deepest point to tip
	theta = atan(d/l); // Angle of stylus
	delta = o ? d*sin(theta) : 0; // Horizontal distance from head of wedge to greatest depth

	translate([x, y, z])
	rotate([0, 0, phi])
	translate([-delta, 0, 0])
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

module singlestroke(x, y, w, h){ // Vertical, positioned from top left corner
	w2 = min(h, w, MAX_STROKE_WIDTH);
	wedge(x+w/2, y, 0, w2, h, 90);
}

module doublestroke(x, y, w, h){
	w2 = min(h, w, MAX_STROKE_WIDTH);
	dist = min(w2, h/4);
	h2 = h - dist;
	h3 = h2 / 2;
	wedge(x+w/2, y, 0, w2, h3, 90);
	wedge(x+w/2, y+dist, 0, w2, h2, 90);
}

module triplestroke(x, y, w, h){
	w2 = min(h, w, MAX_STROKE_WIDTH);
	dist = min(w2, h/4);
	h2 = h - dist*2;
	h3 = min(h2/2, h-dist*2);
	wedge(x+w/2, y, 0, w2, h3, 90);
	wedge(x+w/2, y+dist, 0, w2, h3, 90);
	wedge(x+w/2, y+dist*2, 0, w2, h2, 90);
}

module hookstroke(x, y, w, h, factor=0.75){
//	hh = (w-h/2<0.0001) ? factor*h : h; // By default, the renderer produces hakens that are twice as tall as they are wide - but that means d = 0!
	// We fix this by reducing h by a factor < 1, when this happens
	// Comparing against epsilon instead of zero because transferring numbers from Python to SCAD can do weird things occasionally
	// Experiment: changing w instead of h to make hakens wider, which makes them more visible when they're pressed against verticals
	ww = (w-h/2<0.0001) ? w/factor : w;
	s = h / sqrt(2);
	d = sqrt(ww*ww - h*h/4);
	delta = (ww-w);
	haken(x-delta, y+h/2, 0, s, d); // Use h instead of hh because the haken() module wants the position of the tip, and that needs to be at the midpoint of the *original* bounding box
}

module hrule(y, w, h=0.05){
	s = h*sqrt(2)/2;
	translate([0, y, -s])
		rotate([45, 0, 0])
			cube([w, h, h]);
}

module hatcharea(x, y, w, h){
	// TODO
}