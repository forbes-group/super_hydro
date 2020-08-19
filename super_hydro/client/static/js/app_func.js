// Animation framework function.
function drawCustom(data, nx, ny) {
  sh.x_space = width/nx;
  sh.y_space = height/ny;
  var tmpcanvas = document.createElement("canvas");
  tmpcanvas.width = nx;
  tmpcanvas.height = ny;
  var tmpctx = tmpcanvas.getContext("2d");

  var dataBinding = dataContainer.selectAll("custom")
                                       .data(data);
  var enterSel = dataBinding.enter()
                                  .append("custom");
  dataBinding = dataBinding.merge(enterSel);

  ctxDensity.clearRect(0, 0, chartDensity.attr("width"), chartDensity.attr("height"));

  var elements = dataContainer.selectAll("custom");

  elements.each(function(d, i) {
    tmpctx.fillStyle = "rgb("+ d +","+ d +","+(255-d)+")";
    tmpctx.fillRect(Math.floor(i/nx), (i%ny),
                     1, 1)
  });
  ctxDensity.drawImage(tmpcanvas, 0, 0, nx, ny, 0, 0, width, height)
}

//Finger and Potential layer function.
function drawFinger(fx, fy, vx, vy) {
  vxNew = vx*width;
  vyNew = vy*height;

  ctxFinger.clearRect(0, 0, chartFinger.attr("width"), chartFinger.attr("height"));
  ctxFinger.fillStyle = "444444";
  ctxFinger.beginPath();
  ctxFinger.arc(fx, fy, 5, 0, Math.PI*2, true);
  ctxFinger.fill();
  ctxFinger.beginPath();
  ctxFinger.arc(vxNew, vyNew, 5, 0, Math.PI*2, true);
  ctxFinger.fill();
}
