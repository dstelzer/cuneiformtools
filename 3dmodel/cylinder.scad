// Taken from
// https://openhome.cc/eGossip/OpenSCAD/2DtoCylinder.html

module one_over_fn_for_circle(radius, fn) {
    a = 360 / fn;
    x = radius * cos(a / 2);
    y = radius * sin(a / 2);
    polygon(points=[[0, 0], [x, y],[x, -y]]);
}

module cylindrify(length, width, square_thickness, fn) {
    r = length / 6.28318;
    a = 360 / fn;
    y = r * sin(a / 2);
    for(i = [0 : fn - 1]) {
        // line up the triangle
        rotate(a * i) translate([0, -(2 * y * i + y), 0])

         intersection() {
            // line up the triangle
            translate([0, 2 * y * i + y, 0]) 
                linear_extrude(width) 
                    one_over_fn_for_circle(r, fn);
            // make the character stand up
            translate([r - square_thickness, 0, width]) 
                rotate([0, 90, 0]) 
                    children(0);
        }
    }
}