/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global d3, params */
/* global Timeplot, Clusterer, initial_load */
/* global fullrange, startdate, enddate, time_data */

class Data {
  constructor(labels) {
    this.labels = labels;
    this._data = {};
    this.labels.forEach((label) => {
      this._data[label] = 0;
    });
  }

  update(from, to) {
    if (from) {
      this._data[from] -= 1;
    }
    this._data[to] += 1;
  }

  value(prop, val) {
    this._data[prop] = val;
  }

  data(date) {
    var rv = {};
    if (date) rv.date = date;
    Object.assign(rv, this._data);
    return rv;
  }
}

var data, data0, X;

const dashboardHistoryUrl = (function() {
  const link = document.head.querySelector("link[rel=locale-tree-history]");
  const history_url = new URL(link.href);
  history_url.searchParams.set("tree", link.dataset.tree);
  history_url.searchParams.set("starttime", params.get("starttime"));
  history_url.searchParams.set("endtime", params.get("endtime"));
  return history_url;
}());

class ProgressPlot {
  constructor(timeplot) {
    this.timeplot = timeplot;
    this.params = params;
  }

  compute_states() {
    const graphlabels = ['good', 'shady', 'bad'];
    if (this.params.has("top_locales")) graphlabels.unshift('top_locales');
    let state = new Data(graphlabels);
    let current_states = {}, current_top_state = {};
    this.current_missing = {};
    this.states_over_time = time_data.map(
      (at_time) => {
        Object.assign(this.current_missing, at_time.locales);
        let changed_locales = {}, skip = true;
        Object.entries(at_time.locales).forEach(([loc, missing]) => {
          let isGood = this._getState(missing);
          if (isGood !== current_states[loc]) {
            changed_locales[loc] = isGood;
            skip = false;
          }
        });
        if (params.has("top_locales")) {
          let this_top_state = this.missing_after_top_locales(this.current_missing, params.get("top_locales"));
          if (
            this_top_state.locale !== current_top_state.locale
            || this_top_state.missing !== current_top_state.missing
          ) {
            state.value('top_locales', this_top_state);
            current_top_state = this_top_state;
            skip = false;
          }
        }
        if (skip) {
          return false;
        }
        Object.entries(changed_locales).forEach(([loc, isGood]) => {
          state.update(current_states[loc], isGood);
        });
        Object.assign(current_states, changed_locales);
        state.value('changed_locales', changed_locales);
        return state.data(at_time.srctime);
      }
    ).filter((_state) => _state);
    this.states_over_time.push(state.data(enddate));
  }

  _getState(count) {
    if (count === 0) return 'good';
    if (count > this.params.get("bound")) return 'bad';
    return 'shady';
  }

  missing_after_top_locales(current, cut_off) {
    if (cut_off <= 0) {
      return 0;
    }
    const vals = Object.entries(current).sort((l, r) => l[1] - r[1]);
    const rv = vals[cut_off - 1];
    return {
      locale: rv[0],
      missing: rv[1],
    };
  }
}

class Tooltip {
  constructor(parent) {
    this.plot = parent;
  }

  render() {
    this.tooltipElt = document.getElementById('locales-tooltip');
    this.goodLocalesElt = this.tooltipElt.querySelector('.good');
    this.shadyLocalesElt = this.tooltipElt.querySelector('.shady');
    this.badLocalesElt = this.tooltipElt.querySelector('.bad');
    this.percElt = this.tooltipElt.querySelector('.top_locales')
    let tp = this.plot.timeplot;
    let svg = tp.svg;

    // Create the transparent white box that follows the mouse and shows the
    // considered time range.
    const whiteBoxWidth = 20; // pixels
    this.whiteBoxOffset = whiteBoxWidth / 2;
    this.whiteBox = svg.append("g").append("rect");
    this.whiteBox.attr("x", -9999)
      .attr("y", tp.y(0) - tp.height - 1)
      .attr("width", whiteBoxWidth)
      .attr("height", tp.height)
      .style("fill", "white")
      .style("stroke", "white")
      .style("opacity", "0.2");

    // Define a new element that is the size of the graph, and that is used to
    // detect the mouse movements. As this element is on top in the DOM, this
    // ensures all mouse events will be caught.
    this.graphZone = svg.append("g").append("rect");
    this.graphZone.attr("x", 0)
      .attr("y", tp.y(0) - tp.height - 1)
      .attr("width", tp.width)
      .attr("height", tp.height)
      .style("opacity", 0);

    // Hide and show the tooltip and the white box.
    this.graphZone
      .on("mousemove", () => this.showLocalesTooltip())
      .on("mouseout", () => this.hideTooltip());

    this.tooltipElt.addEventListener("mouseover", () => this.showTooltip());
    this.tooltipElt.addEventListener("mouseout", () => this.hideTooltip());
  }

  // Return the latest state of each locale that changed in a time window.
  findChanges(startTime, endTime) {
    let final_states = {}, triagedLocales = {
      good: [],
      bad: [],
      shady: []
    };
    for (let _state of this.plot.states_over_time) {
      if (_state.date < startTime) continue;
      if (_state.date > endTime) break;
      Object.assign(final_states, _state.changed_locales);
    }
    Object.entries(final_states).forEach(
      ([loc, endState]) => triagedLocales[endState].push(loc)
    );
    return triagedLocales;
  }

  showTooltip() {
    this.whiteBox.style("opacity", 0.2);
    this.tooltipElt.style.display = 'block';
  }

  hideTooltip() {
    this.whiteBox.style("opacity", 0);
    this.tooltipElt.style.display = 'none';
  }

  showLocalesTooltip() {
    const plot = this.plot;
    const tp = plot.timeplot;
    // First update the position of the white box.
    let mouseX = d3.mouse(this.graphZone.node())[0];
    this.whiteBox.attr("x", mouseX - this.whiteBoxOffset);

    // Then compute the list of changing locales in this range.
    var triagedLocales = this.findChanges(
      tp.x.invert(mouseX - this.whiteBoxOffset),
      tp.x.invert(mouseX + this.whiteBoxOffset)
    );
    if (plot.params.has("top_locales")) {
      var date = tp.x.invert(mouseX), i = 0;
      while (plot.states_over_time[i] && plot.states_over_time[i].date < date) ++i;
      var datum = plot.states_over_time[i-1].top_locales;
      dashboardHistoryUrl.searchParams.set("locale", datum.locale);
      this.percElt.innerHTML = `${datum.missing} (<a href="${dashboardHistoryUrl}">${datum.locale}</a>)`;
      dashboardHistoryUrl.searchParams.delete('locale');
      this.percElt.parentElement.style.display = '';
    }
    else {
      this.percElt.parentElement.style.display = 'none';
    }

    // Finaly show those locales in the tooltip box.
    this.showLocalesInElement(triagedLocales.good, this.goodLocalesElt);
    this.showLocalesInElement(triagedLocales.bad, this.badLocalesElt);
    this.showLocalesInElement(triagedLocales.shady, this.shadyLocalesElt);

    if (mouseX > tp.width / 2) {
      this.tooltipElt.style.right = (tp.width - mouseX) + "px";
      this.tooltipElt.style.left = "auto";
    }
    else {
      this.tooltipElt.style.left = mouseX + "px";
      this.tooltipElt.style.right = "auto";
    }

    this.showTooltip();
  }

  // Utility function to add a list of locales to a DOM element.
  showLocalesInElement(locales, element) {
    // Maximum number of elements that will be shown in the reduced tooltip.
    const clipTreshold = 4;

    if (locales.length === 0) {
      element.textContent = "-";
      return;
    }

    element.innerHTML = '';
    locales.forEach((locale, i) => {
      let linkElt = document.createElement("a");
      dashboardHistoryUrl.searchParams.set("locale", locale);
      linkElt.href= dashboardHistoryUrl;
      linkElt.textContent = locale;
      if (i >= clipTreshold) {
        linkElt.className = "clip";
      }
      element.appendChild(linkElt);
    });
    dashboardHistoryUrl.searchParams.delete("locale");
    if (element.lastChild.classList.contains("clip")) {
      element.classList.add("clipping");
      element.appendChild(document.createElement("span"));
    }
    else {
      element.classList.remove("clipping");
    }
  }
}

function renderPlot() {
  var tp = new Timeplot("#my-timeplot");
  var svg = tp.graph_layer;
  X = tp.x;

  const plot = new ProgressPlot(tp);
  data = plot;
  plot.compute_states();
  var layers = ['good', 'shady'];
  if (!params.has("hideBad")) {
    layers.push('bad');
  }
  data0 = d3.stack()
    .keys(layers)
    .order(d3.stackOrderNone)
    .offset(d3.stackOffsetNone)(
      plot.states_over_time
    );
  var area = d3.area()
    .curve(d3.curveStepAfter)
    .x((d) => tp.x(d.data.date))
    .y0((d) => tp.y(d[0]))
    .y1((d) => tp.y(d[1]));
  let yDomain = [0, 0], y2Domain;
  if (params.has("hideBad")) {
    yDomain[1] = d3.max(plot.states_over_time.map((d) => d.good + d.shady));
  }
  else {
    yDomain[1] = d3.max(plot.states_over_time.map((d) => d.good + d.shady + d.bad));
  }
  yDomain[1] += 10;
  if (params.has("top_locales")) {
    y2Domain = [0, d3.max(plot.states_over_time.map((d) => d.top_locales.missing)) * 1.1 + 10];
  }
  tp.drawAxes([startdate, enddate], fullrange, yDomain, y2Domain, params);
  svg.selectAll("path.progress")
    .data(data0)
    .enter()
    .append("path")
    .attr("class", "progress")
    .style("stroke", "black")
    .style("fill", (d, i) => ['#339900', 'grey', '#990000'][i])
    .attr("d", area);
  if (params.has("top_locales")) {
    var percLine = d3.line()
      .curve(d3.curveStepAfter)
      .x((d) => tp.x(d.date))
      .y((d) => tp.y2(d.top_locales.missing));
    svg.append("path")
      .attr("class", "top_locales")
      .attr("d", percLine(plot.states_over_time));
  }

  tp.showMilestones();

  const tooltip = new Tooltip(plot);
  tooltip.render();

  missing_plot.show(plot.current_missing);
  document.getElementById('my-timeplot').addEventListener('click', onClickPlot);
  document.getElementById('boundField').value = params.get("bound") || 0;
  document.getElementById('showBadField').checked = !params.has("hideBad");
  document.getElementById('perctField').value = params.get("top_locales");
}

function update(args) {
  for (const k of Object.keys(args)) {
    if (k === 'hideBad') {
      if (args[k]) {
        params.set('hideBad', true);
      }
      else {
        params.delete('hideBad');
      }
    }
    else {
      params.set(k, args[k]);
    }
  }
  renderPlot();
}

function onClickPlot(evt) {
  var t = X.invert(evt.offsetX);
  var d = {};
  for (var i = 0; i < time_data.length && time_data[i].srctime < t; ++i) {
    Object.assign(d, time_data[i].locales);
  }
  missing_plot.show(d, evt.controlKey || evt.metaKey);
}

class LocalesMissingPlot {
  constructor() {
    this.root = document.querySelector('#percentile');
    this.kown_graphs = [];
    let x_scale = d3.scaleSqrt();
    let y_scale = d3.scaleLinear();
    this.x_axis = d3.axisBottom(x_scale);
    this.y_axis = d3.axisLeft(y_scale);
    this.c_scale = d3.scaleOrdinal(d3.schemeCategory10);
    this.x_axis.scale().domain([0, 0]);
    this.y_axis.scale().domain([0, 0]);
    this.svg = d3.select('#percentile').html('').append("svg");
    let render = this.svg.append("g")
      .attr("class", "render");

    // Add the x-axis.
    render.append("svg:g")
      .attr("class", "x axis");
    // Add the y-axis.
    render.append("svg:g")
      .attr("class", "y axis");
    this.line = d3.line()
      .curve(d3.curveStepAfter)
      .x((point) => x_scale(point.x))
      .y((point) => y_scale(point.percentile));
  }

  show(snapshot, add=false) {
    if (!add) {
      this.known_graphs = [];
      this.x_axis.scale().domain([0, 0]);
      this.y_axis.scale().domain([0, 0]);
    }
    snapshot = this.process(snapshot);
    this.known_graphs.push(snapshot);
    this.render();
    paintHistogram(snapshot);
  }

  process(d) {
    let missing2locales = new Map();
    let locales = Object.keys(d);
    locales.forEach((locale) => {
      const missing = d[locale];
      if (missing2locales.has(missing)) {
        missing2locales.get(missing).push(locale);
      }
      else {
        missing2locales.set(missing, [locale]);
      }
    });
    let list = Array.from(missing2locales).sort((l, r) => l[0] - r[0])
    this.x_axis.scale()
      .domain([
        0,
        Math.max(this.x_axis.scale().domain()[1], list[list.length - 1][0] * 1.1)
      ]);
    this.y_axis.scale()
      .domain([
        0,
        Math.max(this.y_axis.scale().domain()[1], locales.length)
      ]);
    let last = 0;
    return list.map(([_x, _missing]) => ({
      x: _x,
      locales: _missing.sort(),
      percentile: (last += _missing.length),
    }));
  }

  render () {
    let xmargin = 40, ymargin = 40;
    let {width, height} = window.getComputedStyle(this.root);
    width = +(width.replace('px', '')) - 2*xmargin;
    height = +(height.replace('px', '')) - 2*ymargin;
    let x_scale = this.x_axis.scale();
    let y_scale = this.y_axis.scale();
    x_scale.range([0, width]);
    y_scale.range([height, 0]);
    this.c_scale.domain([0, this.known_graphs.length])
    this.svg
      .attr("width", width + xmargin)
      .attr("height", height + 2*ymargin)
    this.svg.select("g.render")
      .attr("transform", "translate(" + xmargin + "," + ymargin + ")");

    // Render the x-axis.
    this.svg.select("g.x.axis")
      .attr("transform", "translate(0," + height + ")")
      .call(this.x_axis);
    // Render the y-axis.
    this.svg.select("g.y.axis")
      .call(this.y_axis);
    let bound = this.svg.select("g.render").selectAll("path.perc_line")
      .data(this.known_graphs);
    bound.exit().remove();
    bound
      .attr("stroke", (_, i) => this.c_scale(i))
      .attr("d", this.line);
    bound
      .enter()
      .append("path")
      .attr("class", "perc_line")
      .attr("fill", "none")
      .attr("stroke", (_, i) => this.c_scale(i))
      .attr("stroke-width", 1.5)
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("d", this.line);
  }
}

const missing_plot = new LocalesMissingPlot();

function paintHistogram(current_missing) {
  const barwidth = 7;
  let missing_values = current_missing.map((cm) => cm.x);
  var smooth = Math.sqrt;
  var clusterer = new Clusterer(missing_values, smooth);
  var ranges = clusterer.get_ranges(4);
  let i = 0, j = 0;
  let maxcount = 1;
  let hists = ranges.map(
    ({min, max}) => {
      for (; j < current_missing.length && current_missing[j].x <= max; ++j) {
        continue
      }
      let rv = {
        count: 0,
        values: current_missing.slice(i, j),
        width: 0,
        min,
        max
      };
      let _left, previous_x = null;
      rv.values.forEach((val) => {
        let {x, locales} = val;
        maxcount = Math.max(maxcount, locales.length);
        if (previous_x === null) {
          _left = 0;
        }
        else {
          _left = (smooth(x - 1) - smooth(previous_x)) * barwidth;
        }
        val.left = Number(_left).toFixed(1) + 'px';
        rv.count += locales.length;
        rv.width += _left + barwidth;
        previous_x = x;
      });
      i=j;
      return rv;
    }
  );

  // histogram
  var chart_height = 100;
  function display_f(_v) {
    return Math.pow(_v, 3 / 4);
  }
  var scale = chart_height * 1.0 / display_f(maxcount);
  let graph_cells = d3.select("#histogram tr.hist.graph")
    .selectAll("td.jazz")
    .data(hists);
  graph_cells.exit().remove();
  graph_cells.enter()
    .append("td")
    .attr("class", "jazz");
  graph_cells = d3.select("#histogram tr.hist.graph")
    .selectAll("td.jazz")
    .data(hists);
  let bars = graph_cells
    .attr("title", (d) => d.count)
    .style("width", (d) => d.width + "px")
    .selectAll("div.spark")
    .data((d) => d.values);
  bars.exit().remove();
  bars.enter().append("div")
    .attr("class", "spark");
  graph_cells
    .selectAll("div.spark")
    .data((d) => d.values)
    .styles({
      height: (d) => display_f(d.locales.length) * scale - 1 + 'px',
      width: barwidth - 2 + 'px',
      "margin-left": (d) => d.left
    })
    .attr("title", (d) => `${d.x}: ${d.locales.join(" ")} (${d.locales.length})`);
  let descs = d3.select("#histogram tr.hist.desc")
    .selectAll("td.desc")
    .data(hists);
  descs.exit().remove();
  descs.enter()
    .append("td")
    .attr("class", "desc")
    .text((d) => (d.min === d.max ? d.min : `${d.min} - ${d.max}`));
  descs.text((d) => (d.min === d.max ? d.min : `${d.min} - ${d.max}`));
}

initial_load();
