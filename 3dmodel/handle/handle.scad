use <polyround.scad>;

// Lengths are in millimeters
// So we provide a convenience
IN2MM = 25.4;

HANDLE_WIDTH = 4 * IN2MM;
HANDLE_LENGTH = 2 * IN2MM;
HANDLE_THICKNESS = 8;
HANDLE_DEPTH = 8;
HANDLE_BRACE = 10;

ROD_DIAMETER = 9;
ROD_SNAP_DIAM = 5;
ROD_END_WIDTH = 5;

TOL = 1.5; // Tolerance where moving parts meet

NOTCH_SQUISH = 0.55;
NOTCH_SIZE = max(HANDLE_DEPTH-(ROD_SNAP_DIAM+TOL), 2.5);

ENDCAP_SIZE = ROD_DIAMETER; // To make things easier
CURVE_RADIUS = 1.5*HANDLE_THICKNESS;

GRAB_LENGTH = 4 * IN2MM;
GRAB_DIAM = 1 * IN2MM;
GRAB_OFFSET = 1 * IN2MM;

GRAB_SQUISH = 0.9;

$fn = 30 * ($preview ? 1 : 5);

INCLUDE_ROD = false;
INCLUDE_HANDLE = true;

module handle_side(){
	translate([0, -HANDLE_LENGTH/2, 0])
	difference(){
		union(){ // Main side plus outer circle on the end
			translate([0, ENDCAP_SIZE/2, 0])
				cube([HANDLE_THICKNESS, ENDCAP_SIZE, HANDLE_DEPTH], center=true);
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

if(INCLUDE_ROD){
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
}

if(INCLUDE_HANDLE){
/*
// Handle base
translate([0, HANDLE_LENGTH, 0]){
%	cube([HANDLE_WIDTH+HANDLE_THICKNESS, HANDLE_THICKNESS, HANDLE_DEPTH], center=true);
	linear_extrude(HANDLE_DEPTH, center=true)
		polygon([[-HANDLE_WIDTH/2, 0], [-HANDLE_WIDTH/2+HANDLE_BRACE, 0], [-HANDLE_WIDTH/2, -HANDLE_BRACE]]);
	linear_extrude(HANDLE_DEPTH, center=true)
		polygon([[HANDLE_WIDTH/2, 0], [HANDLE_WIDTH/2-HANDLE_BRACE, 0], [HANDLE_WIDTH/2, -HANDLE_BRACE]]);
}
*/
// Handle sides
translate([HANDLE_WIDTH/2, HANDLE_LENGTH/2, 0])
	handle_side();
translate([-HANDLE_WIDTH/2, HANDLE_LENGTH/2, 0])
	handle_side();

// Alternate version with polygon
linear_extrude(HANDLE_DEPTH, center=true)
{
	// This is mostly a lot of trial and error until it lined up with the previous version, shown in ghost mode
	outer_width = HANDLE_WIDTH/2 + HANDLE_THICKNESS/2;
	inner_width = outer_width - HANDLE_THICKNESS;
	end_length = HANDLE_LENGTH - HANDLE_THICKNESS/2 - ENDCAP_SIZE;
	inner_length = 0;
	outer_length = -HANDLE_THICKNESS;
	
	translate([0, HANDLE_LENGTH-HANDLE_THICKNESS/2, 0])
	scale([1, -1, 1])
	union(){
		polygon(polyRound([
			// These are (X, Y, Radius) triples
			[-outer_width, outer_length, CURVE_RADIUS+HANDLE_THICKNESS],
			[-outer_width, end_length, 0],
			[-inner_width, end_length, 0],
			[-inner_width, inner_length, CURVE_RADIUS],
			[-0, inner_length, CURVE_RADIUS+HANDLE_THICKNESS/2],
			[0, -HANDLE_THICKNESS, 0],
			[0, inner_length, CURVE_RADIUS+HANDLE_THICKNESS/2],
			[inner_width, inner_length, CURVE_RADIUS],
			[inner_width, end_length, 0],
			[outer_width, end_length, 0],
			[outer_width, outer_length, CURVE_RADIUS+HANDLE_THICKNESS],
			[HANDLE_THICKNESS, outer_length, CURVE_RADIUS],
			[HANDLE_THICKNESS, outer_length-GRAB_OFFSET, 0],
			[-HANDLE_THICKNESS, outer_length-GRAB_OFFSET, 0],
			[-HANDLE_THICKNESS, outer_length, CURVE_RADIUS]
		], $fn));
		polygon([
			[inner_width/2, inner_length],
			[inner_width/2, outer_length],
			[-inner_width/2, outer_length],
			[-inner_width/2, inner_length]
		]);
	}
}

// Handle handle
translate([0, HANDLE_LENGTH+GRAB_OFFSET, 0]) {
//	rotate([90, 0, 0])
//		cylinder(GRAB_OFFSET, d=HANDLE_DEPTH);
	difference(){
		scale([1, 1, GRAB_SQUISH])
		union(){
			sphere(d=GRAB_DIAM);
			translate([0, GRAB_LENGTH, 0]) {
				rotate([90, 0, 0])
					cylinder(GRAB_LENGTH, d=GRAB_DIAM);
				sphere(d=GRAB_DIAM);
			}
		}
		// Flatten the bottom to improve printability
		translate([-HANDLE_WIDTH/2, -GRAB_DIAM, -GRAB_DIAM-HANDLE_DEPTH/2-NOTCH_SIZE])
			cube([HANDLE_WIDTH, GRAB_LENGTH+GRAB_DIAM*2, GRAB_DIAM]);
	}
}

}
