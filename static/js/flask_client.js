// Functions for the Flask client.  This is loaded by the `model.html` template.
//

// document.getElementById("density"): <canvas> on which to draw the density.
function FlaskClient (name, document_) {
 //////////////////////////////////////////////////////////////////////
 // Private Variables

 var model = {
  name: name,
 };

 // Create the canvas Density display element
 var densityCanvas = DensityCanvas(document_.getElementById("density"), model, document_);
 var fingerCanvas = FingerCanvas(document_.getElementById("finger"), model, document_);
 var tracerCanvas = TracerCanvas(document_.getElementById("tracers"), model, document_);

 //Event listener for User mouse-click interaction/placement of potential
 //finger on Canvas display element.
 const getCanvas = document_.querySelector('canvas#finger')
 fingerCanvas.canvas.addEventListener('mousedown', function(e) {
  getCursorPosition(fingerCanvas.canvas, e)
 });

 // FPS tracking
 var _timeStart = new Date().getTime();
 var _timeEnd = new Date().getTime();
 var _pingTimes = [];
 
 //////////////////////////////////////////////////////////////////////
 // Public Interface
 // setParam() ties with 'param_up' socket event to update changes in user
 // controllable parameter values.

 var socket = io('/modelpage');

 function setParam(name, value, logarithmic) {
  model.Param = {};
  if (logarithmic) {
   model.Param[name] = Math.pow(10, value);
  } else {
   model.Param[name] = value;
  }
  socket.emit('set_param', {data: model.name, param: model.Param});
 };

 // doAction() passes action calls to the server.
 function doAction(button) {
  socket.emit('do_action', {data: model.name, name: button.name});
 };

 // This section provides mouseclick/touchscreen interaction for finger
 // potential.
 function getCursorPosition(canvas, event) {
  const rect = canvas.getBoundingClientRect()
  model.fy = (event.clientY - rect.top);
  model.fx = (event.clientX - rect.left);
  const fPos = {'xy0' : [model.fy/(rect.bottom-rect.top),
                         model.fx/(rect.right-rect.left)]}
  socket.emit('finger', {data: model.name, position: fPos})
 };

 
 function doUpdate(data) {
  // Update the display.  This is called asyncrhonously whenever there is
  // updated density information.
  
  densityCanvas.draw(data.rgba);
  let width = densityCanvas.canvas.width;
  let height = densityCanvas.canvas.height;
  
  model.fx = fingerCanvas.canvas.width - data.fxy[1]*fingerCanvas.canvas.width;
  model.fy = data.fxy[0]*fingerCanvas.canvas.height;

  if (data.hasOwnProperty("trace")) {
   tracerCanvas.draw(data.trace, model.nx, model.ny, width, height);
  }
  
  // FPS Counter tracking:
  _timeEnd = new Date().getTime();
  latency = _timeEnd - _timeStart;
  _pingTimes.push(latency);
  _pingTimes = _pingTimes.slice(-30); //keep last 30 samples
  var sum = 0;
  for (var i = 0; i < _pingTimes.length; i++)
   sum += _pingTimes[i];
  model.fps = Math.floor(10000/ Math.round(10 * sum / _pingTimes.length));
  document.getElementById('ping-pong').innerHTML = model.fps;
  _timeStart = _timeEnd;
  
  //Draw the Finger Potential (placed last to allow consistent FPS tracking)
  //vbytes = Uint8Array.from(data.vxy, c => c.charCodeAt(0));
  //vfloats = new Float64Array(vbytes.buffer);
  //var vfloats = data.vxy;
  //fingerCanvas.draw(model.fx, model.fy, vfloats[1], vfloats[0],
   //                  densityCanvas.canvas.width, densityCanvas.canvas.height);
 //                  densityCanvas.canvas.width, densityCanvas.canvas.height);
   
 };


 function on_resize () {
  let containers = document_.getElementsByClassName('containers');
  let heightDiff = 0;
  for (c = 0; c < containers.length; ++c) {
   heightDiff += containers[c].offsetHeight;
  }

  let width = densityCanvas.canvas.width;
  let height = densityCanvas.canvas.height;
  if (width > (window.innerHeight - heightDiff)) {
   width = window.innerHeight - heightDiff;
  } else if (height > width) {
	 height = width;
  } else {
	 width = window.innerWidth;
	 height = window.innerHeight - heightDiff;
  }
  
  densityCanvas.resize(width, height);
 }
 
 return {
  fingerCanvas: fingerCanvas,
  model: model,
  on_resize: on_resize,
  socket: socket,
  doUpdate: doUpdate,
  setParam: setParam,
  doAction: doAction,
 }
};

function DensityCanvas (canvas, model, document_) {
 // Manages the density canvas.
 var ctx = canvas.getContext("2d");   // ctxDensity
 var tmpcanvas = document_.createElement("canvas");
 var tmpctx = tmpcanvas.getContext("2d");

 function resize (width, height) {
  canvas.width = width;
  canvas.height = height;
 };

 function draw (rgba) {
  let rgba_ = Uint8ClampedArray.from(rgba, c => c.charCodeAt(0))
  let nx = model.nx;
  let ny = model.ny;
  let image_data = new ImageData(rgba_, nx);
  let width = canvas.width;
  let height = canvas.height;
  let im_width = nx;
  let im_height = ny;
  
  if (height < window.innerWidth) {
	 width = height * nx / ny;
  } else {
	 height = width * ny / nx;
  }
  
  if (width == im_width && height == im_height) {
   // Simply draw.
   canvas.width = width;
   canvas.height = height;
   ctx.putImageData(image_data, 0, 0);
  } else {
   // Pre-render on background canvas, then scale
   tmpcanvas.width = im_width;
   tmpcanvas.height = im_height;
   tmpctx.putImageData(image_data, 0, 0);
   
   canvas.width = width;
   canvas.height = height;
   ctx.drawImage(tmpcanvas,
                 0, 0, im_width, im_height,
                 0, 0, width, height);
  }  
 };
 
 return {
  canvas: canvas,
  ctx: ctx,
  resize: resize,
  draw: draw,
 }
};

function FingerCanvas (canvas, model, document_) {
 // Manages the finger canvas.
 var ctx = canvas.getContext("2d");   // ctxFinger

 function resize (width, height) {
  canvas.width = width;
  canvas.height = height;
 };

 function draw (fx, fy, vx, vy, width, height) {
  vxNew = vx*canvas.width;
  vyNew = vy*canvas.height;
  potSize = document_.getElementById('finger_V0_mu').value

  if (height < window.innerWidth) {
	 canvas.width = height;
  } else {
	 canvas.height = width;
  }

  ctx.clearRect(0, 0, width, height);

  ctx.beginPath();
  ctx.fillStyle = "Black";
  ctx.arc(fx, fy, 5, 0, Math.PI*2, true);
  ctx.fill();
  ctx.beginPath();
  ctx.strokeStyle = "White";
  ctx.arc(vxNew, vyNew, 8, 0, Math.PI*2, true);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(fx, fy);
  ctx.lineTo(vxNew, vyNew);
  ctx.stroke();
 };
 
 return {
  canvas: canvas,
  draw: draw,
  ctx: ctx,
  resize: resize,
 }
};


function TracerCanvas (canvas, model, document_) {
 // Manages the tracer canvas.
 var ctx = canvas.getContext("2d");   // ctxTracer

 function resize (width, height) {
  canvas.width = width;
  canvas.height = height;
 };

 function draw (trace, nx, ny, width, height) {
	if (height < window.innerWidth) {
	 canvas.width = height;
	} else {
	 canvas.height = width;
	}

	ctx.clearRect(0,0,width,height);

	var i;
	for (i=0; i < trace[0].length; i++) {
	 ctx.beginPath();
	 ctx.arc(trace[1][i] / nx * width, trace[0][i] / ny * height, 2, 0, 2*Math.PI);
	 ctx.stroke();
	}
 }

 return {
  canvas: canvas,
  draw: draw,
  ctx: ctx,
  resize: resize,
 }
};

