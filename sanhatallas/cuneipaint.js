// Requires victor.min.js
// https://github.com/maxkueng/victor
const Vec = Victor // Because I don't like spelling it that way
Vec.prototype.scale = function(scalar){ // WHY IS THIS NOT INCLUDED
	this.x *= scalar;
	this.y *= scalar;
	return this;
}

const Style = {
	NONE : 'NONE',
	STROKE : 'STROKE',
	DOUBLE : 'DOUBLE',
	HOOK : 'HOOK',
	DIVIDE : 'DIVIDE',
	PROGRESS : 'PROGRESS',
	DELETE : 'DELETE',
}

var strokes = []; // Objects with type (String), head (Vec), tail (Vec)

var tool = Style.STROKE; // Currently selected tool
var anchor; // Anchor point (where the first click was made)
var anchored = false; // Becomes true after one click, false after another click
var cursor;

var canvas;
var ctx;
var output;

var parsed;

// Figure out how close the cursor is to either the anchor or a specific stroke
const CLOSENESS_THRESHOLD = 10;
const THRESHOLD_SQUARED = CLOSENESS_THRESHOLD ** 2;
function close_to_anchor(){
	return anchor.distanceSq(cursor) <= THRESHOLD_SQUARED;
}
function close_to_hook(stroke){ // Check if within AABB, it's easier
	var height = stroke.head.distance(stroke.tail);
	var left = stroke.head.x - height/4;
	var right = stroke.head.x + height/4;
	return cursor.x >= left && cursor.x <= right && cursor.y >= stroke.head.y && cursor.y <= stroke.tail.y;
}
function close_to_stroke(stroke){
	if(stroke.type == Style.HOOK) return close_to_hook(stroke);
	// https://stackoverflow.com/a/1501725/3233017
	// Squared length of stroke
	var strokevec = stroke.tail.clone().subtract(stroke.head); // w-v
	var l2 = strokevec.lengthSq();
	// To avoid dividing by zero in a degenerate case
	if(l2 == 0) return cursor.distanceSq(stroke.head) <= THRESHOLD_SQUARED;
	// Calculate (p-v) dot (w-v)
	var pminusv = cursor.clone().subtract(stroke.head); // p-v
	var dot = pminusv.dot(strokevec);
	// Position of the closest point along the stroke, normalized
	var t = clamp(dot/l2, 0, 1);
	// And that point itself
	var proj = stroke.head.clone().mix(stroke.tail, t); // Linear blend
	return proj.distanceSq(cursor) <= THRESHOLD_SQUARED;
}
function clamp(x, low, high){
	return Math.min(high, Math.max(low, x));
}

function finalize_stroke(){
	if(tool == Style.HOOK) return finalize_hook();
	
	strokes.push({type:tool, head:anchor.unfloat(), tail:cursor.unfloat()}); // We don't need to call the normalize function here because the server will handle that for us
	anchored = false;
	anchor = null; // Shouldn't matter, but avoids leaving a reference around that could get modified
}
function finalize_hook(){
	// Make 1x2 rectangle, taken from draw_stroke...any way to reduce redundancy here?
	var width = anchor.absDistanceX(cursor);
	var height = anchor.absDistanceY(cursor);
	var center = anchor.clone().mix(cursor, 0.5); // Midpoint
	if(width < height/2){ // Use the lower of the two dimensions
		height = width*2;
	}else{
		width = height/2;
	}
	if(width < 10){ // Raise to the minimum if needed
		width = 10;
		height = 20;
	}
	
	var head = Vec(center.x, center.y-height/2); // NW
	var tail = Vec(center.x, center.y+height/2); // SE
	
	strokes.push({type:tool, head:head.unfloat(), tail:tail.unfloat()});
	anchored = false;
	anchor = null;
}

function normalize_stroke(stroke){ // Make sure strokes don't point backwards, for aesthetic purposes only
	var theta = stroke.tail.clone().subtract(stroke.head).angle();
	if(theta > Math.PI*9/16 || theta <= -Math.PI*7/16)
		return {type:stroke.type, head:stroke.tail, tail:stroke.head}; // Invert
	else
		return stroke;
}

function draw_stroke(stroke){
	var deletion = (tool == Style.DELETE && close_to_stroke(stroke)); // Is this stroke about to get deleted?
	var pending = (stroke.type == Style.PROGRESS); // Is this stroke currently being drawn?
	if(pending) stroke.type = tool; // If so, what tool is it being drawn with?
	
	ctx.beginPath();
	
	switch(stroke.type){
		case Style.STROKE: // Basic stroke
		case Style.DOUBLE: // Double-headed stroke
			ctx.setLineDash([]); // No dashes
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'black';
			
			stroke = normalize_stroke(stroke);
			
			var smallstroke = stroke.tail.clone().subtract(stroke.head).normalize().scale(20); // Direction of stroke, scaled down to 20 units
			var halfhead = smallstroke.clone().rotateDeg(90); // The head stroke that should extend in both directions from the end of the line segment
			ctx.moveTo(stroke.head.x + halfhead.x, stroke.head.y + halfhead.y);
			ctx.lineTo(stroke.head.x - halfhead.x, stroke.head.y - halfhead.y);
			
			// If it's double-headed, draw a second head too
			if(stroke.type == Style.DOUBLE){
				ctx.moveTo(stroke.head.x + smallstroke.x + halfhead.x, stroke.head.y + smallstroke.y + halfhead.y);
				ctx.lineTo(stroke.head.x + smallstroke.x - halfhead.x, stroke.head.y + smallstroke.y - halfhead.y);
			}
			
			ctx.moveTo(stroke.head.x, stroke.head.y);
			ctx.lineTo(stroke.tail.x, stroke.tail.y);
			
			break;
		
		case Style.HOOK: // Hook stroke
			// Make a 1x2 rectangle out of the stroke
			var width = stroke.head.absDistanceX(stroke.tail);
			var height = stroke.head.absDistanceY(stroke.tail);
			var center = stroke.head.clone().mix(stroke.tail, 0.5); // Midpoint
			
			if(pending){ // If pending, use the actual width and height
				if(width < height/2){ // Use the lower of the two dimensions
					height = width*2;
				}else{
					width = height/2;
				}
			}else{ // Otherwise, it's just a vertical line
				width = height/2;
			}
			
			if(width < 10){ // Raise to the minimum if needed
				width = 10;
				height = 20;
			}
			
			var halfwidth = width/2;
			var halfheight = height/2;
			
			ctx.setLineDash([]); // No dashes
			
			if(pending){ // Show the actual pen movement if it's pending
				ctx.lineWidth = 1;
				ctx.strokeStyle = 'blue';
				ctx.moveTo(stroke.head.x, stroke.head.y);
				ctx.lineTo(stroke.tail.x, stroke.tail.y);
				ctx.stroke();
				ctx.beginPath();
			}
			
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'black';
			ctx.moveTo(center.x+halfwidth, center.y-halfheight); // NE
			ctx.lineTo(center.x-halfwidth, center.y); // W
			ctx.lineTo(center.x+halfwidth, center.y+halfheight); // SE
			
			break;
		
		case Style.DIVIDE: // Dividing line
			ctx.setLineDash([20, 20]);
			ctx.lineWidth = 5;
			ctx.strokeStyle = 'blue';
			
			ctx.moveTo(stroke.head.x, stroke.head.y);
			ctx.lineTo(stroke.tail.x, stroke.tail.y);
			
			break;
		
		default: // Something went wrong
			ctx.setLineDash([]);
			ctx.lineWidth = 1;
			ctx.strokeStyle = 'magenta';
			
			ctx.moveTo(stroke.head.x, stroke.head.y);
			ctx.lineTo(stroke.tail.x, stroke.tail.y);
			
			break;
	}
	
	if(deletion){ // Override color if it's primed for deletion
		ctx.strokeStyle = 'gray';
	}
	ctx.stroke();
}

function redraw(){
	ctx.clearRect(0, 0, canvas.width, canvas.height);
	strokes.forEach(draw_stroke);
	if(anchored){ // Also draw the current stroke
		draw_stroke({type:Style.PROGRESS, head:anchor, tail:cursor});
	}
}
function set_cursor(e){
	rect = canvas.getBoundingClientRect();
	x = e.clientX - rect.left;
	y = e.clientY - rect.top;
	cursor = Vec(x, y);
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
	set_cursor(e);
	
	if(tool == Style.DELETE){ // The delete tool is suggested
		for(var i=strokes.length-1; i>=0; i--){ // Run through the strokes backward
			if(close_to_stroke(strokes[i])){ // This stroke was clicked
				strokes.splice(i, 1); // Remove it
				redraw(); // Redraw the canvas
				return; // And only remove one stroke per click
			}
		}
	}else if(anchored){ // There's a stroke in progress
		if(close_to_anchor()){ // And we're too close to the origin
			anchored = false; // Take that as a sign to end it
			redraw();
		}
	}else{ // We're starting a new stroke
		anchor = cursor.clone();
		anchored = true;
		redraw();
	}
}

// Mouse comes up on the canvas
function cvs_up(e){
	set_cursor(e);
	
	if(anchored){ // There's a stroke in progress
		if(!close_to_anchor()){ // And we're far enough away for it to be valid
			finalize_stroke();
			redraw();
		}
	}
}

// Mouse moves on the canvas
function cvs_move(e){
	set_cursor(e);
	redraw();
}

// "Stroke" button to draw strokes
function btn_stroke(){
	tool = Style.STROKE;
	output.innerHTML = 'Draw strokes';
}

// "Double" button to draw double-headed strokes
function btn_double(){
	tool = Style.DOUBLE;
	output.innerHTML = 'Draw double-headed strokes';
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
	redraw();
	clear_preview();
	btn_stroke();
}

// "Submit" button to parse the results
function btn_submit(){
	data = JSON.stringify(strokes); // The raw data we're sending
	console.log("send: "+data);
	code = encodeURIComponent(data);
	var xhttp = new XMLHttpRequest();
	xhttp.onload = function(){
		console.log("resp: " + this.responseText);
		var resp = JSON.parse(this.responseText);
		handle_server_response(resp);
	}
	
	var url = "/cuneipaint_parse?tolerance=10&code="+code;
	var params = new URLSearchParams(document.location.search); // Check if we have an expkey on this page
	if(params.has("expkey")){ // Make sure the experiment key is preserved
		url = url +"&expkey="+ params.get("expkey");
	}
	
	console.log("url: " + url);
	xhttp.open("GET", url);
	xhttp.send();
}

function handle_server_response(obj){
	if(obj.success){
		parsed = obj.result;
		output.innerHTML = '<tt>' + parsed + '</tt>';
		var code = encodeURIComponent(parsed);
		var url = "/rendersign?code=" + code + "&format=svg&type=publish&scale=160";
		document.getElementById("preview").src = url;
		document.getElementById("searchbutton").disabled = false;
	}else{
		output.innerHTML = 'Problem! ' + obj.result; // Error message
		clear_preview();
	}
}

function clear_preview(){
	var url = "/rendersign?code=0&format=svg&scale=160";
	document.getElementById("preview").src = url;
	document.getElementById("searchbutton").disabled = true;
}

function resize_preview(){ // Change the size of the preview element, called by preview element's onload
	var p = document.getElementById("preview");
	p.style.width = p.contentWindow.document.documentElement.scrollWidth + 'px';
	p.style.height = p.contentWindow.document.documentElement.scrollHeight + 'px';
}

// "Search" button to search for the parsed results
function btn_search(){
	var code = encodeURIComponent(parsed);
	var params = new URLSearchParams(document.location.search); // Check if we have an expkey on this page
	var url = "/search?code="+ code +"&sort=complex";
	if(params.has("expkey")){ // Make sure the experiment key is preserved
		url = url +"&expkey="+ params.get("expkey");
	}
//	document.location = url; // TODO: new tab instead?
	window.open(url, "_blank");
}
