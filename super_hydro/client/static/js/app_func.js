// Takes an array and converts it to JSON object with x-y coordinates
// for each value.

function arr_conv(data) {
  xs = [];
  ys = [];
  vals = [];
  var i;
  var j;

  for (i in data){
    for (j in data[i]) {
      if ( xs.includes(i) && ys.includes(j) ){
        vals.push({"x" : i, "y": j, "density": data[i][j]});
      }
      else if ( xs.includes(i) ) {
        ys.push(j);
        vals.push({"x" : i, "y": j, "density": data[i][j]});
      }
      else if ( ys.includes(j) ) {
        xs.push(i);
        vals.push({"x" : i, "y": j, "density": data[i][j]});
      }
      else {
        xs.push(i);
        ys.push(j);
        vals.push({"x" : i, "y": j, "density": data[i][j]});
      }
    }
  }
  return vals;
};

// Animation framework function.

function up_disp(data) {

  var myColor = d3.scaleLinear()
                  .range(["blue", "yellow"])
                  .domain([0,1]);

  d3.selectAll('rect')
    .data(data)
    .style("fill", function(d) { return myColor(d.density) });
};

// Display area.
function make_disp(data) {

  var x = d3.scaleBand()
            .range([ 0, width ])
            .domain(xs)
            .padding(0.01);

  // Build X scales and axis:
  var y = d3.scaleBand()
            .range([ height, 0 ])
            .domain(ys)
            .padding(0.01);

  // Build color scale
  var myColor = d3.scaleLinear()
                  .range(["blue", "yellow"])
                  .domain([0,1])

  svg.selectAll()
     .data(data, function(d) { return d.x+':'+d.y})
     .enter()
     .append("rect")
     .attr("id", function(d) { return d.x+d.y })
     .attr("x", function(d) { return x(d.x) })
     .attr("y", function(d) { return y(d.y) })
     .attr("width", x.bandwidth())
     .attr("height", y.bandwidth())
     .style("fill", function(d) { return myColor(d.density) });
};
