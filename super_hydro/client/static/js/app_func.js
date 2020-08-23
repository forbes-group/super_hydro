// Animation framework function.
function drawCustom(rgba, nx, ny) {
  var image_data = new ImageData(rgba, nx);
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
    canvasDensity.width = width;
    canvasDensity.height = height;
    ctxDensity.putImageData(image_data, 0, 0);
  } else {
    // Pre-render on background canvas, then scale
    var tmpcanvas = document.createElement("canvas");
    var tmpctx = tmpcanvas.getContext("2d");
    tmpcanvas.width = im_width;
    tmpcanvas.height = im_height;
    tmpctx.putImageData(image_data, 0, 0);

    baseDensity.attr("width", width)
                .attr("height", height);
    //chartDensity.height = height;
    canvasDensity.width = width;
    canvasDensity.height = height;
    ctxDensity.drawImage(tmpcanvas,
                         0, 0, im_width, im_height,
                         0, 0, width, height);
  }
}

//Finger and Potential layer function.
function drawFinger(fx, fy, vx, vy) {
  vxNew = vx*width;
  vyNew = vy*height;

  ctxFinger.clearRect(0, 0, chartFinger.attr("width"), chartFinger.attr("height"));

  ctxFinger.beginPath();
  ctxFinger.strokeStyle = "White";
  ctxFinger.arc(fx, fy, 5, 0, Math.PI*2, true);
  ctxFinger.stroke();
  ctxFinger.beginPath();
  ctxFinger.fillStyle = "Black";
  ctxFinger.arc(vxNew, vyNew, 5, 0, Math.PI*2, true);
  ctxFinger.fill();
  ctxFinger.beginPath();
  ctxFinger.moveTo(fx, fy);
  ctxFinger.lineTo(vxNew, vyNew);
  ctxFinger.stroke();
}
