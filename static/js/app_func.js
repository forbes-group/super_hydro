// setParam() ties with 'param_up' socket event to update changes in user
// controllable parameter values.
function setParam(name, value) {
 sh.Param = {};
 sh.Param[name] = value;
 socket.emit('set_param', {data: sh.model, param: sh.Param});
};

// setLogParam() ties with 'log_param_up' socket event to update changes in
// user controllable logarithmic scale parameter values.
function setLogParam(name, value) {
  sh.Param = {};
  sh.Param[name] = Math.pow(10, value);
  socket.emit('set_log_param', {data: sh.model, param: sh.Param})
}

// doAction() passes action calls to the server.
function doAction(name) {
 socket.emit('do_action', {data: sh.model, name: name});
};

// This section provides mouseclick/touchscreen interaction for finger
// potential.
function getCursorPosition(canvas, event) {
 const rect = canvas.getBoundingClientRect()
 sh.fy = (event.clientY - rect.top);
 sh.fx = (event.clientX - rect.left);
 const fPos = {'xy0' : [sh.fy/(rect.bottom-rect.top),
                        sh.fx/(rect.right-rect.left)]}
 socket.emit('finger', {data: sh.model, position: fPos})
};

// Animation framework function.
function drawCustom(rgba, nx, ny) {
  var image_data = new ImageData(rgba, nx);
  var width = chartDensity.width;
  var height = chartDensity.height;
  var im_width = nx;
  var im_height = ny;

  if (0 == width && 0 == height) {
    width = im_width;
    height = im_height;
  } else if (0 == height) {
    // Preserve aspect ratio
    height = im_height * width / im_width;
  } else if (0 == width) {
    // Preserve aspect ratio
    width = im_width * height / im_height;
  }

  if (width == im_width && height == im_height) {
    // Simply draw.
    chartDensity.width = width;
    chartDensity.height = height;
    ctxDensity.putImageData(image_data, 0, 0);
  } else {
    // Pre-render on background canvas, then scale
    var tmpcanvas = document.createElement("canvas");
    var tmpctx = tmpcanvas.getContext("2d");
    tmpcanvas.width = im_width;
    tmpcanvas.height = im_height;
    tmpctx.putImageData(image_data, 0, 0);

    chartDensity.width = width;
    chartDensity.height = height;
    ctxDensity.drawImage(tmpcanvas,
                         0, 0, im_width, im_height,
                         0, 0, width, height);
  }
}

//Finger and Potential layer function.
function drawFinger(fx, fy, vx, vy) {
  vxNew = vx*chartFinger.width;
  vyNew = vy*chartFinger.height;
  potSize = document.getElementById('finger_V0_mu').value

  ctxFinger.clearRect(0, 0, chartFinger.width, chartFinger.height);

  ctxFinger.beginPath();
  ctxFinger.fillStyle = "Black";
  ctxFinger.arc(fx, fy, 5, 0, Math.PI*2, true);
  ctxFinger.fill();
  ctxFinger.beginPath();
  ctxFinger.strokeStyle = "White";
  ctxFinger.arc(vxNew, vyNew, 8, 0, Math.PI*2, true);
  ctxFinger.stroke();
  ctxFinger.beginPath();
  ctxFinger.moveTo(fx, fy);
  ctxFinger.lineTo(vxNew, vyNew);
  ctxFinger.stroke();
}

//Tracer Particle layer function.
function drawTracer(trace, nx, ny) {
  var image_data = new ImageData(trace, nx);
  var width = chartTracer.width;
  var height = chartTracer.height;
  var im_width = nx;
  var im_height = ny;

  if (0 == width && 0 == height) {
    width = im_width;
    height = im_height;
  } else if (0 == height) {
    // Preserve aspect ratio
    height = im_height * width / im_width;
  } else if (0 == width) {
    // Preserve aspect ratio
    width = im_width * height / im_height;
  }

  if (width == im_width && height == im_height) {
    // Simply draw.
    chartTracer.width = width;
    chartTracer.height = height;
    ctxTracer.putImageData(image_data, 0, 0);
  } else {
    // Pre-render on background canvas, then scale
    var tmpcanvas = document.createElement("canvas");
    var tmpctx = tmpcanvas.getContext("2d");
    tmpcanvas.width = im_width;
    tmpcanvas.height = im_height;
    tmpctx.putImageData(image_data, 0, 0);

    chartTracer.width = width;
    chartTracer.height = height;
    ctxTracer.drawImage(tmpcanvas,
                         0, 0, im_width, im_height,
                         0, 0, width, height);
  }
}
