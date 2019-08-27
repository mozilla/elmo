/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global d3, URLSearchParams */
/* global MILESTONES */

/*
 * Generic code to create a view that takes starttime, endtime,
 * and uses two x-axes to select that
 */

class Timeplot {
  constructor(selector, params, options) {
    const defaultoptions = {xmargin: 40, ymargin: 40, yAxes: 2};
    options = Object.assign({}, defaultoptions, options);
    let {width, height} = window.getComputedStyle(
      document.querySelector(selector)
    );
    this.width = +(width.replace('px', '')) - options.yAxes*options.xmargin;
    this.height = +(height.replace('px', '')) - 3*options.ymargin;
    var x = d3.time.scale()
      .range([0, this.width]);
    var x2 = d3.time.scale()
      .range([0, this.width]);

    var y = d3.scale.linear()
      .range([this.height, 0]);
    var y2 = d3.scale.linear()
      .range([this.height, 0]);

    var xAxis = d3.svg.axis().scale(x).orient("bottom"),
      xAxis2 = d3.svg.axis().scale(x2).orient("bottom"),
      yAxis = d3.svg.axis().scale(y).orient("left"),
      yAxis2 = d3.svg.axis().scale(y2).orient("right");

    this.svg = d3.select(selector).html('').append("svg")
      .attr("width", this.width + options.yAxes*options.xmargin)
      .attr("height", this.height + 3*options.ymargin)
      .attr("class", "timeline")
      .append("g")
      .attr(
        "transform",
        `translate(${options.xmargin},${options.ymargin})`
      );

    // Add the x-axis.
    this.svg.append("svg:g")
      .attr("class", "x axis")
      .attr("transform", `translate(0,${this.height})`);
    // Add the x-axis.
    this.svg.append("svg:g")
      .attr("class", "x2 axis")
      .attr("transform", `translate(0,${this.height + options.ymargin})`);
    // Add the y-axis.
    this.svg.append("svg:g")
      .attr("class", "y axis");
    // Add the y2-axis.
    this.svg.append("svg:g")
      .attr("class", "y2 axis")
      .attr("transform", `translate(${this.width},0)`);
    this.graph_layer = this.svg.append("g")
      .attr("class", "graph layer");
    this.milestone_layer = this.svg.append("g")
      .attr("class", "milestone layer");
    this.brush = d3.svg.brush()
      .x(x);
    this.brush.on("brushend", this._onBrushEnd(this.brush, params));
    this.brush2 = d3.svg.brush()
      .x(x2);
    this.brush2.on("brushend", this._onBrushEnd(this.brush2, params));
    this.x = x;
    this.x2 = x2;
    this.y = y;
    this.y2 = y2;
    this.xAxis = xAxis;
    this.xAxis2 = xAxis2;
    this.yAxis = yAxis;
    this.yAxis2 = yAxis2;
    this.options = options;
  }

  drawAxes(xDomain, fullXDomain, yDomain, y2Domain) {
    this.x.domain(xDomain);
    this.x2.domain(fullXDomain);
    this.y.domain(yDomain);
    if (y2Domain) {
      this.y2.domain(y2Domain);
    }
    this.brush2.extent(xDomain);
    this.svg.select("g.x.axis").call(this.xAxis);
    this.svg.select("g.x2.axis").call(this.xAxis2);
    this.svg.select("g.y.axis").call(this.yAxis);
    if (y2Domain) {
      this.svg.select("g.y2.axis").call(this.yAxis2);
    }
    this.svg.select("g.x.axis").append("g")
      .attr("class", "x brush")
      .call(this.brush)
      .selectAll("rect")
      .attr("height", this.options.ymargin);
    this.svg.select("g.x2.axis").append("g")
      .attr("class", "x2 brush")
      .call(this.brush2)
      .selectAll("rect")
      .attr("height", this.options.ymargin);
  }

  showMilestones() {
    let ticks = this.milestone_layer
      .selectAll("g.milestone.tick")
      .data(MILESTONES, (ms) => ms.version);
    ticks.exit().remove();
    ticks.select("text").attr("x", (ms) => this.x(ms.time));
    ticks.select("rect").attr("x", (ms) => this.x(ms.time));
    let inner = ticks.enter()
      .append("g")
      .attr("class", "milestone tick");
    inner
      .append("text")
      .attr("x", (ms) => this.x(ms.time))
      .attr("y", this.y(0) - this.height - 1)
      .style("text-anchor", "middle")
      .text((ms) => ms.version);
    inner
      .append("rect")
      .attr("x", (ms) => this.x(ms.time))
      .attr("y", this.y(0) - this.height + 10)
      .attr("width", 1)
      .attr("height", this.height / 4)
      .style("fill", "black");
  }

  _onBrushEnd(_brush, params) {
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
}

function formatRoundedDate(d) {
  let round = new Date(
    Math.round(Number(d) / 1000 / 60 / 60 / 24)
    * 1000 * 60 * 60 * 24
  );
  return `${round.getUTCFullYear()}-${round.getUTCMonth() + 1}-${round.getUTCDate()}`;
}
 
