/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global d3, URLSearchParams */

/*
 * Generic code to create a view that takes starttime, endtime,
 * and uses two x-axes to select that
 */

function timeplot(selector, fullrange, domain, params, options) {
  var defaultoptions = {xmargin: 40, ymargin: 40, yAxes: 2};
  if (options) {
    for (var o in defaultoptions) {
      if (defaultoptions.hasOwnProperty(o) && !options.hasOwnProperty(o)) {
        options[o] = defaultoptions[o];
      }
    }
  }
  else {
    options = defaultoptions;
  }
  let {width, height} = window.getComputedStyle(document.querySelector(selector));
  width = +(width.replace('px', '')) - options.yAxes*options.xmargin;
  height = +(height.replace('px', '')) - 3*options.ymargin;
  var x = d3.time.scale()
      .range([0, width]);
  var x2 = d3.time.scale()
      .range([0, width]);

  var y = d3.scale.linear()
      .range([height, 0]);
  var y2 = d3.scale.linear()
      .range([height, 0]);

  var xAxis = d3.svg.axis().scale(x).orient("bottom"),
      xAxis2 = d3.svg.axis().scale(x2).orient("bottom"),
      yAxis = d3.svg.axis().scale(y).orient("left"),
      yAxis2 = d3.svg.axis().scale(y2).orient("right");

  var svg = d3.select(selector).html('').append("svg")
      .attr("width", width + options.yAxes*options.xmargin)
      .attr("height", height + 3*options.ymargin)
      .attr("class", "timeline")
      .append("g")
      .attr("transform", "translate(" + options.xmargin + "," + options.ymargin + ")");

  // Add the x-axis.
  svg.append("svg:g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")");
  // Add the x-axis.
  svg.append("svg:g")
    .attr("class", "x2 axis")
    .attr("transform", "translate(0," + (height + options.ymargin) + ")");
  // Add the y-axis.
  svg.append("svg:g")
    .attr("class", "y axis");
  // Add the y2-axis. XXX
  svg.append("svg:g")
    .attr("class", "y2 axis")
    .attr("transform", "translate(" + width + ",0)");
  var brush = d3.svg.brush()
    .x(x);
  brush.on("brushend", onBrushEnd(brush, params));
  var brush2 = d3.svg.brush()
    .x(x2);
  brush2.on("brushend", onBrushEnd(brush2, params));
  x.domain(domain);
  x2.domain(fullrange);
  brush2.extent(domain);
  // need domains for y?
  svg.select("g.x.axis").call(xAxis);
  svg.select("g.x2.axis").call(xAxis2);
  svg.select("g.x.axis").append("g")
    .attr("class", "x brush")
    .call(brush)
    .selectAll("rect")
    .attr("height", options.ymargin);
  svg.select("g.x2.axis").append("g")
    .attr("class", "x brush")
    .call(brush2)
    .selectAll("rect")
    .attr("height", options.ymargin);
  return {
    svg: svg,
    height: height,
    width: width,
    x: x,
    y: y,
    y2: y2,
    yDomain: function(d) {
      y.domain(d);
      svg.select("g.y.axis").call(yAxis);
    },
    y2Domain: function(d) {
      y2.domain(d);
      svg.select("g.y2.axis").call(yAxis2);
    }
  };
}

function formatRoundedDate(d) {
  var floor, ceil, round;
  floor = new Date(d);
  floor.setUTCHours(0);
  floor.setUTCMinutes(0);
  floor.setUTCSeconds(0);
  floor.setUTCMilliseconds(0);
  ceil = new Date(floor);
  ceil.setUTCDate(ceil.getUTCDate() + 1);
  round = ceil - d < d - floor ? ceil : floor;
  return round.getUTCFullYear() +
    '-' + (round.getUTCMonth() + 1) +
    '-' + round.getUTCDate();
}

function onBrushEnd(_brush, params) {
  return function() {
    if (_brush.empty()) return;
    var extent = _brush.extent();
    var domain = _brush.x().domain();
    var _p = new URLSearchParams(), sd, ed;
    if (extent[0] - domain[0]) {
      // set start date only if it's not start of time
      sd = extent[0];
      _p.set('starttime', formatRoundedDate(sd));
    }
    if (extent[1] - domain[1]) {
      ed = _brush.extent()[1];
      _p.set('endtime', formatRoundedDate(ed));
    }
    if (params) {
      for (var k in params) {
        if (params.hasOwnProperty(k) && ! _p.hasOwnProperty(k)) {
          _p.set(k, params[k]);
        }
      }
    }
    document.location.search = '?' + _p;
  };
}

function showMilestones(tp) {
  var milestone, ms_label, ms_tick;
  for (milestone of MILESTONES) {
    ms_label = tp.svg.append("text");
    ms_label.attr("x", tp.x(milestone.time))
    .attr("y", tp.y(0) - tp.height - 1)
    .style("text-anchor", "middle")
    ms_label.text(milestone.version);
    ms_tick = tp.svg.append("rect");
    ms_tick.attr("x", tp.x(milestone.time))
    .attr("y", tp.y(0) - tp.height + 10)
    .attr("width", 1)
    .attr("height", tp.height / 4)
    .style("fill", "black");
  }
}
