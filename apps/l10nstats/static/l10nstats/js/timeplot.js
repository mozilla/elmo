/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global d3, URLSearchParams */

/*
 * Generic code to create a view that takes starttime, endtime,
 * and uses two x-axes to select that
 */


var params = new URL(document.location).searchParams;
var time_data, startdate, enddate, fullrange, MILESTONES;

async function initial_load() {
  const link = document.head.querySelector("link[rel=api]");
  const api_url = new URL(link.href);
  for (const [k, v] of params.entries()) {
    api_url.searchParams.set(k, v);
  }
  let response = await d3.json(api_url);
  time_data = response.data.map(
    (row) => {
      row.srctime = new Date(row.srctime * 1000);
      return row;
    }
  );
  MILESTONES = response.milestones.map(
    (ms) => {
      ms.time = new Date(ms.timestamp * 1000);
      return ms;
    }
  );
  startdate = new Date(response.stamps.start * 1000);
  enddate = new Date(response.stamps.end * 1000);
  fullrange = [
    new Date(response.stamps.startrange * 1000),
    new Date(response.stamps.endrange * 1000)
  ]
  renderPlot();
}

class Timeplot {
  constructor(selector, options) {
    const defaultoptions = {xmargin: 40, ymargin: 40, yAxes: 2};
    options = Object.assign({}, defaultoptions, options);
    let {width, height} = window.getComputedStyle(
      document.querySelector(selector)
    );
    this.width = +(width.replace('px', '')) - options.yAxes*options.xmargin;
    this.height = +(height.replace('px', '')) - 3*options.ymargin;
    var x = d3.scaleTime()
      .range([0, this.width]);
    var x2 = d3.scaleTime()
      .range([0, this.width]);

    var y = d3.scaleLinear()
      .range([this.height, 0]);
    var y2 = d3.scaleLinear()
      .range([this.height, 0]);

    var xAxis = d3.axisBottom(x),
      xAxis2 = d3.axisBottom(x2),
      yAxis = d3.axisLeft(y),
      yAxis2 = d3.axisRight(y2);

    this.svg = d3.select(selector).html('').append("svg")
      .attr("width", this.width + options.yAxes*options.xmargin)
      .attr("height", this.height + 3*options.ymargin)
      .attr("class", "timeline")
      .append("g")
      .attr(
        "transform",
        `translate(${options.xmargin},${options.ymargin})`
      );

    // Add the x-axes.
    this.svg.append("svg:g")
      .attr("class", "x axis")
      .attr("transform", `translate(0,${this.height})`);
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

  drawAxes(xDomain, fullXDomain, yDomain, y2Domain, params) {
    this.x.domain(xDomain);
    this.x2.domain(fullXDomain);
    this.y.domain(yDomain);
    if (y2Domain) {
      this.y2.domain(y2Domain);
    }
    this.svg.select("g.x.axis").call(this.xAxis);
    this.svg.select("g.x2.axis").call(this.xAxis2);
    this.svg.select("g.y.axis").call(this.yAxis);
    if (y2Domain) {
      this.svg.select("g.y2.axis").call(this.yAxis2);
    }
    this.brush = d3.brushX();
    this.brush.extent([[0, 0], [this.x.range()[1], this.options.ymargin]]);
    this.brush2 = d3.brushX();
    this.svg.select("g.x.axis").append("g")
      .attr("class", "x brush")
      .call(this.brush);
    let b2 = this.svg.select("g.x2.axis").append("g")
      .attr("class", "x2 brush")
      .call(this.brush2);
    this.brush2.move(b2, xDomain.map(this.x2));
    this.brush.on("end", this._onBrushEnd(this.x, params));
    this.brush2.on("end", this._onBrushEnd(this.x2, params));
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

  _onBrushEnd(axis, params) {
    return function() {
      if (!d3.event.sourceEvent) return;
      let selection = d3.event.selection;
      if (!selection) return;
      selection = selection.map(axis.invert);
      var domain = axis.domain();
      var _p = new URLSearchParams(), sd, ed;
      if (selection[0] !== domain[0]) {
        // set start date only if it's not start of time
        sd = selection[0];
        _p.set('starttime', formatRoundedDate(sd));
      }
      if (selection[1] !== domain[1]) {
        ed = selection[1];
        _p.set('endtime', formatRoundedDate(ed));
      }
      if (params) {
        for (let [k, v] of params.entries()) {
          if (! _p.has(k)) {
            _p.set(k, v);
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
