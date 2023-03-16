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

//wedge(0, 0, 0, 10, 30, 30);
//haken(0, 0, 0, 20);

/*
difference(){
	translate([0, 0, -2.5])
		cube([60, 40, 5], center=true);
	wedge(-25, 0, 0, 10, 30, 0);
	wedge(-10, 0, 0, 10, 30, 0);
	wedge(5, 15, 0, 10, 30, -90);
	haken(10, 0, 0, 10, 5);
}
*/

scale([1,-1,1]){
	difference(){
		translate([0,0,-2.5])
			cube([12,12,2.5]);
		union(){
			translate([1,1,0]){
				scale([10,10,10]){
					rotate(-90.0){
						wedge(-0.5000000000000001, 0, 0, 0.3333333333333333, 0.4166666666666667, 90);
					}
					rotate(-90.0){
						wedge(-0.5000000000000001, 0.4166666666666667, 0, 0.3333333333333333, 0.4166666666666667, 90);
					}
					wedge(0.8333333333333334, 0, 0, 0.3333333333333333, 1, 90);
				}
			}
		}
	}
}




