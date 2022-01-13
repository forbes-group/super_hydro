// Functions for the Flask client.  This is loaded by the `model.html` template.
//

// document.getElementById("density"): <canvas> on which to draw the density.
function FlaskClient(name, document_) {
 //////////////////////////////////////////////////////////////////////
 // Public Interface
 // When a use changes an input on the UI, this is onChange() is called.
 // This then emits a set_param() message to the python client.
 function onChange(name, value, logarithmic) {
  let params = {};
  if (logarithmic) {
   value = Math.pow(10, value);
  }
  params[name] = value;
  socket.emit('set_params', {model_name: model.name, params: params});
 };

 //////////////////////////////////////////////////////////////////////
 // Private
 var model = {
  name: name,
  params: ['Nx', 'Ny', 'finger_x', 'finger_y'],
  f_xy: [0.5, 0.5],
  v_xy: [0.5, 0.5],
 };

 // Add all input widgets
 for (let input of document.getElementsByTagName('input')) {
  model.params.push(input.id);
 }
 

 // Create the canvas Density display element
 var densityCanvas = DensityCanvas(document_.getElementById("density"), model, document_);
 var fingerCanvas = FingerCanvas(document_.getElementById("finger"), model, document_);
 var tracerCanvas = TracerCanvas(document_.getElementById("tracers"), model, document_);

 // FPS tracking
 var _timeStart = new Date().getTime();
 var _timeEnd = new Date().getTime();
 var _pingTimes = [];
 
 var socket = io('/modelpage');

 function doUpdate(data) {
  // Update the display.  This is called asyncrhonously whenever there is
  // updated density information.
  
  densityCanvas.draw(data.rgba);
  let width = densityCanvas.canvas.width;
  let height = densityCanvas.canvas.height;

  if (data.hasOwnProperty("f_xy")) {
   model.f_xy = data["f_xy"];
   model.v_xy = data["v_xy"];
   fingerCanvas.draw(model);
  }
  
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
 };
 
 // Resize all of the widgets.
 function resize() {
  let containers = document_.getElementsByClassName('containers');
  let heightDiff = 0;
  for (c = 0; c < containers.length; ++c) {
   heightDiff += containers[c].offsetHeight;
  }

  let nx = model.nx;
  let ny = model.ny
  let width = window.innerWidth;
  let height = window.innerHeight - heightDiff;

  if (width / height < nx / ny) {
   // Space is too tall for canvas - use full width.
   height = ny * width / nx;
  } else {
   // Space is too wide for canvas - use full height.
   width = nx * height / ny;
  }
  
  densityCanvas.resize(width, height);
  fingerCanvas.resize(width, height);
  tracerCanvas.resize(width, height);
 }
  
 //Socket data reception to update user display for slider interactions,
 //regardless of which connected user interacted.
 function setParams(params) {
  for (let key in params) {
   let widget = document_.getElementById(key);
   let value_label = document_.getElementById('val_' + key);
   let value = params[key];
   
   value_label.innerHTML = value;
   if (widget.type == 'checkbox') {
    widget.checked = value;
   } else if (widget.name == 'logarithmic') {
    widget.value = Math.log10(value);
   } else {
    widget.value = value;
   }
  }
 }

 function onConnect() {
  // When the User socket connection is made, start a server if not running
  socket.emit('start_srv', {name: model.name, params: model.params})
 }
 
 function updateWidgets(data) {
  // Update all of the widgets and their values.
  Object.keys(data).forEach(key => {
   let widget = document_.getElementById(key);
   let label = document_.getElementById('val_' + key);
   let value = data[key];
   
   if (widget) { // Make sure input exists first.
    label.innerHTML = value;

    if (widget.type == 'checkbox') {
     widget.checked = value;
    } else {
     // Sliders
     if (widget.name == 'logarithmic') {
      value = Math.log10(value);
     }
     widget.value = value;
    }
   }
  });
  
  // Set model size
  model.nx = data.Nx;
  model.ny = data.Ny;

  // Resize window.
  resize();
 }

 // This section provides mouseclick/touchscreen interaction for finger
 // potential.
 function getCursorPosition(event) {
  const canvas = fingerCanvas.canvas;
  const rect = canvas.getBoundingClientRect();
  return [
   (event.clientX - rect.left) / (rect.right - rect.left),
   (event.clientY - rect.bottom) / (rect.top - rect.bottom)];
 }

 let mouse_down = false;
 function moveFinger(f_xy) {
  model.f_xy = f_xy;
  setParams({finger_x: f_xy[0], finger_y: f_xy[1]});
  socket.emit('finger', {data: model.name, f_xy: f_xy});
  fingerCanvas.draw(model);
 }
 
 function onMouseDown(e) {
  mouse_down = true;
  moveFinger(getCursorPosition(e));
 }
 
 function onMouseUp(e) {
  mouse_down = false;
 }
 
 function onMouseMove(e) {
  if (mouse_down) {
   moveFinger(getCursorPosition(e));
  }
 }
 
 //////////////////////////////////////////////////////////////////////
 // Connect event listeners and callbacks
 //
 // Handlers called by Python through the socket
 socket.on('update', doUpdate);
 socket.on('set_params', setParams);
 socket.on('connect', onConnect);
 socket.on('update_widgets', updateWidgets);
 
 // Event listener for User mouse-click interaction/placement of potential
 // finger on Canvas display element.
 // const getCanvas = document_.querySelector('canvas#finger')
 fingerCanvas.canvas.addEventListener('mousedown', onMouseDown)
 fingerCanvas.canvas.addEventListener('mouseup', onMouseUp)
 fingerCanvas.canvas.addEventListener('mousemove', onMouseMove)

 for (let button of document.getElementsByTagName("button")) {
  button.addEventListener("click", function () {
   socket.emit('click', {data: model.name, name: this.name});
  })
 };

 // Auto-scale Model Animation to available window whitespace area.
 window.onload = window.onresize = resize;

 //When User navigates away from page, informs Flask framework to update user
 //count. This may result in computational server being shut down if room is
 //empty.
 window.onbeforeunload = function () {
  socket.emit('user_exit', {'data': model.name});
 }
 
 return {
  onChange: onChange,
 }
};

function DensityCanvas(canvas, model, document_) {
 // Manages the density canvas.
 var ctx = canvas.getContext("2d");   // ctxDensity
 var tmpcanvas = document_.createElement("canvas");
 var tmpctx = tmpcanvas.getContext("2d");

 function resize(width, height) {
  canvas.width = width;
  canvas.height = height;
 };

 function draw(rgba) {
  let rgba_ = Uint8ClampedArray.from(rgba, c => c.charCodeAt(0))
  let nx = model.nx;
  let ny = model.ny;
  let image_data = new ImageData(rgba_, nx, ny);
  let width = canvas.width;
  let height = canvas.height;
  let im_width = nx;
  let im_height = ny;
  
  if (width == im_width && height == im_height) {
   // Simply draw.
   ctx.putImageData(image_data, 0, 0);
  } else {
   // Pre-render on background canvas, then scale
   tmpcanvas.width = im_width;
   tmpcanvas.height = im_height;
   tmpctx.putImageData(image_data, 0, 0);
   
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

function FingerCanvas(canvas, model, document_) {
 // Manages the finger canvas.
 var ctx = canvas.getContext("2d");   // ctxFinger

 function resize(width, height) {
  canvas.width = width;
  canvas.height = height;
 };

 function draw(data) {
  let fx = data.f_xy[0] * canvas.width;
  let fy = (1 - data.f_xy[1]) * canvas.height;

  let vx = data.v_xy[0] * canvas.width;
  let vy = (1 - data.v_xy[1]) * canvas.height;

  // Finger size is 10% of minimum width
  let fr = 0.1*Math.min(canvas.width, canvas.height);

  // Should compute this from finger_r.
  let vr = 0.1*Math.min(canvas.width, canvas.height);

  //potSize = document_.getElementById('finger_V0_mu').value

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.beginPath();
  ctx.fillStyle = "Black";
  ctx.arc(fx, fy, 5, 0, Math.PI*2, true);
  ctx.fill();
  ctx.beginPath();
  ctx.strokeStyle = "White";
  ctx.arc(vx, vy, 8, 0, Math.PI*2, true);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(fx, fy);
  ctx.lineTo(vx, vy);
  ctx.stroke();
 };
 
 return {
  canvas: canvas,
  draw: draw,
  ctx: ctx,
  resize: resize,
 }
};


function TracerCanvas(canvas, model, document_) {
 // Manages the tracer canvas.
 var ctx = canvas.getContext("2d");   // ctxTracer

 function resize(width, height) {
  canvas.width = width;
  canvas.height = height;
 };

 function draw(trace, nx, ny, width, height) {
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

