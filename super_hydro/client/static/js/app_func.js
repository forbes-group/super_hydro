// Animation framework function.


function drawCustom(data) {
  xs = d3.range(64)
  ys = d3.range(64)
  //console.log(xs)

  var x = d3.scaleBand()
            .range([ 0, width ])
            .domain(xs)
            .padding(0);

  // Build X scales and axis:
  var y = d3.scaleBand()
            .range([ height, 0 ])
            .domain(ys)
            .padding(0);

  // Build color scale
  var myColor = d3.scaleLinear()
                  .range(["blue", "yellow"])
                  .domain([0,1])

  var dataBinding = dataContainer.selectAll("custom.rect")
                                 .data(data);

  dataBinding.attr("fillStyle", function(d) {return myColor(d)});

  dataBinding.enter()
             .append("custom")
             .classed("rect", true)
             .attr("id", function(d, i) { return Math.floor(i/64).toString()+'-'+(i%64).toString() })
             .attr("x", function(d, i) { return x(Math.floor(i/64)) })
             .attr("y", function(d, i) { return y(i%64) })
             .attr("width", x.bandwidth())
             .attr("height", y.bandwidth())
             .attr("fillStyle", function(d) { return myColor(d) });

  dataBinding.exit()
             .attr("fillStyle", "lightgrey");

  drawCanvas();
}

function drawCanvas() {
  //clear canvas
  context.fillStyle = "#fff";
  context.rect(0,0,chart.attr("width"), chart.attr("height"));
  context.fill();

  var elements = dataContainer.selectAll("custom.rect");
  elements.each(function(d) {
    var node = d3.select(this);

    context.beginPath();
    context.fillStyle = node.attr("fillStyle");
    context.rect(node.attr("x"), node.attr("y"),
                 node.attr("width"), node.attr("height"))
    context.fill();
    context.closePath();
  });
}
