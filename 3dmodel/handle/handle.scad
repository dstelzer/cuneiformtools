// Lengths are in millimeters
// So we provide a convenience
IN2MM = 25.4;

HANDLE_WIDTH = 3.5 * IN2MM;
HANDLE_LENGTH = 2 * IN2MM;
HANDLE_THICKNESS = 5;
HANDLE_DEPTH = 6;
HANDLE_BRACE = 10;

ROD_DIAMETER = 9;
ROD_SNAP_DIAM = 5;
ROD_END_WIDTH = 8;

TOL = 1.5; // Tolerance where moving parts meet

NOTCH_SQUISH = 0.6;
NOTCH_SIZE = max(HANDLE_DEPTH-(ROD_SNAP_DIAM+TOL), 2.5);

ENDCAP_SIZE = ROD_DIAMETER; // To make things easier

GRAB_LENGTH = 4.5 * IN2MM;
GRAB_DIAM = 1 * IN2MM;
GRAB_OFFSET = 1 * IN2MM;

$fn = 30 * ($preview ? 1 : 5);

module handle_side(){
	translate([0, -HANDLE_LENGTH/2, 0])
	difference(){
		union(){ // Main side plus outer circle on the end
			translate([0, HANDLE_LENGTH/2, 0])
				cube([HANDLE_THICKNESS, HANDLE_LENGTH, HANDLE_DEPTH], center=true);
			rotate([0, 90, 0])
				cylinder(HANDLE_THICKNESS, d=ROD_SNAP_DIAM+TOL+NOTCH_SIZE, center=true);
		}
		union(){ // Inner circle plus angle cutout
			rotate([0, 90, 0])
				cylinder(HANDLE_THICKNESS+TOL, d=ROD_SNAP_DIAM+TOL, center=true);
			scale([1, 1, NOTCH_SQUISH])
			translate([0, -HANDLE_DEPTH*sqrt(2)/2, 0])
			rotate([45, 0, 0])
			rotate([0, 90, 0])
				cube([HANDLE_DEPTH*sqrt(2), HANDLE_DEPTH*sqrt(2), HANDLE_THICKNESS+TOL], center=true);
		}
	}
}

// Rod
translate([0, -HANDLE_LENGTH/2, 0]) // Comment this out to see in situ
rotate([0, 90, 0]) {
	union() {
		cylinder(HANDLE_WIDTH+2*ROD_END_WIDTH, d=ROD_SNAP_DIAM, center=true);
		cylinder(HANDLE_WIDTH-HANDLE_THICKNESS-TOL, d=ROD_DIAMETER, center=true);
		translate([0, 0, (HANDLE_WIDTH+TOL+ROD_END_WIDTH+HANDLE_THICKNESS)/2])
			cylinder(ROD_END_WIDTH, d=ROD_DIAMETER, center=true);
		translate([0, 0, -(HANDLE_WIDTH+TOL+ROD_END_WIDTH+HANDLE_THICKNESS)/2])
			cylinder(ROD_END_WIDTH, d=ROD_DIAMETER, center=true);
	}
}

// Handle base
translate([0, HANDLE_LENGTH, 0]){
	cube([HANDLE_WIDTH+HANDLE_THICKNESS, HANDLE_THICKNESS, HANDLE_DEPTH], center=true);
	linear_extrude(HANDLE_DEPTH, center=true)
		polygon([[-HANDLE_WIDTH/2, 0], [-HANDLE_WIDTH/2+HANDLE_BRACE, 0], [-HANDLE_WIDTH/2, -HANDLE_BRACE]]);
	linear_extrude(HANDLE_DEPTH, center=true)
		polygon([[HANDLE_WIDTH/2, 0], [HANDLE_WIDTH/2-HANDLE_BRACE, 0], [HANDLE_WIDTH/2, -HANDLE_BRACE]]);
}
// Handle sides
translate([HANDLE_WIDTH/2, HANDLE_LENGTH/2, 0])
	handle_side();
translate([-HANDLE_WIDTH/2, HANDLE_LENGTH/2, 0])
	handle_side();

// Alternate version with polygon


// Handle handle
translate([0, HANDLE_LENGTH+GRAB_OFFSET, 0]) {
	rotate([90, 0, 0])
		cylinder(GRAB_OFFSET, d=HANDLE_DEPTH);
	difference(){
		union(){
			sphere(d=GRAB_DIAM);
			translate([0, GRAB_LENGTH, 0]) {
				rotate([90, 0, 0])
					cylinder(GRAB_LENGTH, d=GRAB_DIAM);
				sphere(d=GRAB_DIAM);
			}
		}
		// Flatten the bottom to improve printability
		translate([-HANDLE_WIDTH/2, -GRAB_DIAM, -GRAB_DIAM-HANDLE_DEPTH/2-NOTCH_SIZE+TOL])
			cube([HANDLE_WIDTH, GRAB_LENGTH+GRAB_DIAM*2, GRAB_DIAM]);
	}
}
