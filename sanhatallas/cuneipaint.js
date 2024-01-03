const Style = {
	NONE : 'NONE',
	STROKE : 'STROKE',
	HOOK : 'HOOK',
	DIVIDE : 'DIVIDE',
	PROGRESS : 'PROGRESS',
	DELETE : 'DELETE',
}

var strokes = []; // Objects with type, x1, x2, y1, y2

var tool = Style.STROKE; // Currently selected tool
var anchor_x; // Anchor point (where the first click was made)
var anchor_y;
var anchored = false; // Becomes true after one click, false after another click

var canvas;
var ctx;
var output;

// A bunch of math utilities for dealing with points without creating any actual point objects, which was probably a bad decision but it's what I've got now
const CLOSENESS_THRESHOLD = 10;
function is_close_point(x, y){
	// Standard Euclidean distance
	return distance2(x, anchor_x, y, anchor_y) <= CLOSENESS_THRESHOLD**2;
}
function is_close_line(x, y, stroke){
	// https://stackoverflow.com/a/1501725/3233017
	// Squared length of stroke
	l2 = distance2(stroke.x1, stroke.x2, stroke.y1, stroke.y2);
	// To avoid dividing by zero in a degenerate case
	if(l2 == 0) return distance2(x, stroke.x1, y, stroke.y1) <= CLOSENESS_THRESHOLD**2;
	// Calculate (p-v) dot (w-v)
	dot = (x-stroke.x1)*(stroke.x2-stroke.x1) + (y-stroke.y1)*(stroke.y2-stroke.y1);
	// Position of the closest point along the line segment
	t = clamp(dot/l2, 0, 1);
	// That point itself
	px = stroke.x1 + t*(stroke.x2 - stroke.x1);
	py = stroke.y1 + t*(stroke.y2 - stroke.y1);
	return distance2(x, px, y, py) <= CLOSENESS_THRESHOLD**2;
}
function distance2(x1, x2, y1, y2){ // Distance squared
	return (x2-x1)**2 + (y2-y1)**2;
}
function clamp(x, low, high){
	return Math.min(high, Math.max(low, x));
}

function finalize_stroke(x, y){
	strokes.push({type:tool, x1:anchor_x, y1:anchor_y, x2:x, y2:y});
	anchored = false;
}

function set_style(type){
	switch(type){
		case Style.STROKE:
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'black';
			break;
		case Style.HOOK:
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'red';
			break;
		case Style.DIVIDE:
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'blue';
			break;
		case Style.PROGRESS:
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'green';
			break;
		case Style.DELETE: // This stroke is targetted for deletion
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'gray';
			break;
		default:
			ctx.lineWidth = 1;
			ctx.strokeStyle = 'magenta';
	}
}

function draw_stroke(stroke, deletion=false){
	ctx.beginPath();
	ctx.moveTo(stroke.x1, stroke.y1);
	ctx.lineTo(stroke.x2, stroke.y2);
	set_style(deletion ? Style.DELETE : stroke.type);
	ctx.stroke();
}

function redraw(x, y){
	ctx.clearRect(0, 0, canvas.width, canvas.height);
	for(var i=0; i<strokes.length; i++){
		if(tool == Style.DELETE && is_close_line(x, y, strokes[i])){
			draw_stroke(strokes[i], true);
		}else{
			draw_stroke(strokes[i]);
		}
	}
//	strokes.forEach(draw_stroke);
	if(anchored){ // Also draw the current stroke
		draw_stroke({type:Style.PROGRESS, x1:anchor_x, y1:anchor_y, x2:x, y2:y});
	}
}

// Called at the very beginning when the page loads
function setup(){
	canvas = document.getElementById('paintcanvas');
	ctx = canvas.getContext('2d');
	output = document.getElementById('outputpanel');
	btn_stroke();
}

// Mouse goes down on the canvas
function cvs_down(e){
	rect = canvas.getBoundingClientRect();
	x = e.clientX - rect.left;
	y = e.clientY - rect.top;
	
	if(tool == Style.DELETE){ // The delete tool is suggested
		for(var i=strokes.length-1; i>=0; i--){ // Run through the strokes backward
			if(is_close_line(x, y, strokes[i])){ // This stroke was clicked
				strokes.splice(i, 1); // Remove it
				redraw(x, y); // Redraw the canvas
				return; // And only remove one stroke per click
			}
		}
	}else if(anchored){ // There's a stroke in progress
		if(is_close_point(x, y)){ // And we're too close to the origin
			anchored = false; // Take that as a sign to end it
			redraw(x, y);
		}
	}else{ // We're starting a new stroke
		anchor_x = x;
		anchor_y = y;
		anchored = true;
		redraw(x, y);
	}
}

// Mouse comes up on the canvas
function cvs_up(e){
	rect = canvas.getBoundingClientRect();
	x = e.clientX - rect.left;
	y = e.clientY - rect.top;
	
	if(anchored){ // There's a stroke in progress
		if(!is_close_point(x, y)){ // And we're far enough away for it to be valid
			finalize_stroke(x, y);
			redraw(x, y);
		}
	}
}

// Mouse moves on the canvas
function cvs_move(e){
	rect = canvas.getBoundingClientRect();
	x = e.clientX - rect.left;
	y = e.clientY - rect.top;
	
	redraw(x, y);
}

// "Stroke" button to draw strokes
function btn_stroke(){
	tool = Style.STROKE;
	output.innerHTML = 'Draw strokes';
}

// "Hook" button to draw hooks
function btn_hook(){
	tool = Style.HOOK;
	output.innerHTML = 'Draw hooks';
}

// "Divide" button to draw dividers
function btn_divide(){
	tool = Style.DIVIDE;
	output.innerHTML = 'Draw dividers';
}

// "Delete" button to delete strokes
function btn_delete(){
	tool = Style.DELETE;
	output.innerHTML = 'Delete strokes';
}

// "Clear" button to clear the canvas
function btn_clear(){
	strokes = [];
	redraw(0,0);
}

// "Submit" button to finalize
function btn_submit(){
	alert(JSON.stringify(strokes));
}
