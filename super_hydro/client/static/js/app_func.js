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

  context.clearRect(0, 0, chart.attr("width"), chart.attr("height"));

  var elements = dataContainer.selectAll("custom");

  elements.each(function(d, i) {
    tmpctx.fillStyle = "rgb("+ d +","+ d +","+(255-d)+")";
    tmpctx.fillRect(Math.floor(i/nx), (i%ny),
                     1, 1)
  });
  context.drawImage(tmpcanvas, 0, 0, nx, ny, 0, 0, width, height)
}
