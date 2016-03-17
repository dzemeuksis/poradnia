var margin = {top: 20, right: 30, bottom: 30, left: 40},
    width = 960 - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom;

var x = d3.time.scale()
    .range([0, width]);

var y = d3.scale.linear()
    .range([height, 0]);

var color = d3.scale.linear()
    .range(["#abcdef", "#123456"]);

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom");

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var area = d3.svg.area()
    .x(function(d) { return x(d.date); })
    .y0(function(d) { return y(d.y0); })
    .y1(function(d) { return y(d.y0 + d.y); });

var stack = d3.layout.stack()
    .values(function(d) { return d.values; });

var chart = d3.select(".chart")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

function status_chart(error, data) {
  if (error) throw error;

  var parseDate = d3.time.format("%Y%m").parse;
  data.forEach(function(d) {
    d.date = parseDate(d.year.toString() + d.month.toString());
    delete d.year;
    delete d.month;
  });

  x.domain(d3.extent(data, function(d) { return d.date; }));
  y.domain([0, d3.max(data, function(d) { return d.count_closed + d.count_assigned + d.count_open; })]);
  color.domain([0, data.length]);
  xAxis.ticks(data.length);

  var statusNames = d3.keys(data[0]).filter(function(key) { return key !== "date"; });

  var statuses = stack(statusNames.map(function(status) {
      return {
        status: status,
        values: data.map(function(d) {
          return {date: d.date, y: d[status]};
        })
      }
  }));

  chart.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height + ")")
      .call(xAxis);

  chart.append("g")
      .attr("class", "y axis")
      .call(yAxis);

  var status = chart.selectAll(".status")
      .data(statuses)
    .enter().append("g")
      .attr("class", "status")

  status.append("path")
      .attr("class", "area")
      .attr("d", function(d) { return area(d.values); })
      .style("fill", function(d, i) { return color(i); });
}
