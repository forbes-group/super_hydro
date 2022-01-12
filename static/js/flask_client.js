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

  // Set finger
  model.fx = fingerCanvas.canvas.width - data.finger_x * fingerCanvas.canvas.width;
  model.fy = data.finger_y * fingerCanvas.canvas.height;  
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
 fingerCanvas.canvas.addEventListener('mousedown', function(e) {
  getCursorPosition(fingerCanvas.canvas, e)
 });

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

  // if (height < window.innerWidth) {
	//  width = height * nx / ny;
  // } else {
	//  height = width * ny / nx;
  // }
  
  if (width == im_width && height == im_height) {
   // Simply draw.
   // canvas.width = width;
   // canvas.height = height;
   ctx.putImageData(image_data, 0, 0);
  } else {
   // Pre-render on background canvas, then scale
   tmpcanvas.width = im_width;
   tmpcanvas.height = im_height;
   tmpctx.putImageData(image_data, 0, 0);
   
   //canvas.width = width;
   //canvas.height = height;
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

 function draw(fx, fy, vx, vy, width, height) {
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

