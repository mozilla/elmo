/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global $, d3, HIDE_BAD, BOUND, top_locales, LOCALE_DATA */
/* global startdate, enddate, fullrange */
/* global Timeplot, formatRoundedDate, Clusterer */

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

var params = {};
if (HIDE_BAD) {
  params.hideBad = true;
}
if (BOUND) {
  params.bound = BOUND;
}
if (top_locales) {
  params.top_locales = top_locales;
}

var data, data0, X;
var loc_data = LOCALE_DATA;

var dashboardHistoryUrl = window.DASHBOARD_HISTORY_URL + "&starttime=" + formatRoundedDate(startdate) + "&endtime=" + formatRoundedDate(enddate) + "&locale="

class ProgressPlot {
  constructor(timeplot) {
    this.timeplot = timeplot;
    this.params = params;
  }

  compute_states() {
    const graphlabels = ['good', 'shady', 'bad'];
    if (this.params.top_locales) graphlabels.unshift('top_locales');
    let state = new Data(graphlabels);
    let current_states = {}, current_top_state = {};
    this.current_missing = {};
    this.states_over_time = loc_data.map(
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
        if (params.top_locales) {
          let this_top_state = this.missing_after_top_locales(this.current_missing, params.top_locales);
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
        return state.data(at_time.time);
      }
    ).filter((_state) => _state);
    this.states_over_time.push(state.data(enddate));
  }

  _getState(count) {
    if (count === 0) return 'good';
    if (count > this.params.bound) return 'bad';
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
    let mouseX = d3.mouse(this.graphZone.flat()[0])[0];
    this.whiteBox.attr("x", mouseX - this.whiteBoxOffset);

    // Then compute the list of changing locales in this range.
    var triagedLocales = this.findChanges(
      tp.x.invert(mouseX - this.whiteBoxOffset),
      tp.x.invert(mouseX + this.whiteBoxOffset)
    );
    if (plot.params.top_locales) {
      var date = tp.x.invert(mouseX), i = 0;
      while (plot.states_over_time[i] && plot.states_over_time[i].date < date) ++i;
      var datum = plot.states_over_time[i-1].top_locales;
      this.percElt.innerHTML = `${datum.missing} (<a href="${dashboardHistoryUrl + datum.locale}">${datum.locale}</a>)`;
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
      linkElt.href= dashboardHistoryUrl + locale;
      linkElt.textContent = locale;
      if (i >= clipTreshold) {
        linkElt.className = "clip";
      }
      element.appendChild(linkElt);
    });
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
  var tp = new Timeplot("#my-timeplot", params);
  var svg = tp.graph_layer;
  X = tp.x;

  const plot = new ProgressPlot(tp);
  data = plot;
  plot.compute_states();
  var layers = ['good', 'shady'];
  if (!params.hideBad) {
    layers.push('bad');
  }
  data0 = d3.layout.stack()(layers.map(
    (k) => plot.states_over_time.map((d) => ({x: d.date, y: d[k]}))
  ));
  var area = d3.svg.area()
    .interpolate("step-after")
    .x((d) => tp.x(d.x))
    .y0((d) => tp.y(d.y0))
    .y1((d) => tp.y(d.y + d.y0));
  let yDomain = [0, 0], y2Domain;
  if (params.hideBad) {
    yDomain[1] = d3.max(plot.states_over_time.map((d) => d.good + d.shady));
  }
  else {
    yDomain[1] = d3.max(plot.states_over_time.map((d) => d.good + d.shady + d.bad));
  }
  yDomain[1] += 10;
  if (params.top_locales) {
    y2Domain = [0, d3.max(plot.states_over_time.map((d) => d.top_locales.missing)) * 1.1 + 10];
  }
  tp.drawAxes([startdate, enddate], fullrange, yDomain, y2Domain);
  svg.selectAll("path.progress")
     .data(data0)
     .enter()
     .append("path")
     .attr("class", "progress")
     .style("stroke", "black")
     .style("fill", (d, i) => ['#339900', 'grey', '#990000'][i])
     .attr("d", area);
  if (params.top_locales) {
      var percLine = d3.svg.line()
      .interpolate('step-after')
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
  document.getElementById('boundField').value = params.bound || 0;
  document.getElementById('showBadField').checked = !params.hideBad;
  document.getElementById('perctField').value = params.top_locales;
}

function update(args) {
  Object.assign(params, args);
  if (params.hasOwnProperty('hideBad') && !params.hideBad) {
    delete params.hideBad;
  }
  renderPlot();
}

function onClickPlot(evt) {
  var t = X.invert(evt.offsetX);
  var d = {};
  for (var i = 0; i < loc_data.length && loc_data[i].time < t; ++i) {
    Object.assign(d, loc_data[i].locales);
  }
  missing_plot.show(d, evt.controlKey || evt.metaKey);
}

class LocalesMissingPlot {
  constructor() {
    this.root = document.querySelector('#percentile');
    this.kown_graphs = [];
    let x_scale = d3.scale.sqrt();
    let y_scale = d3.scale.linear();
    this.x_axis = d3.svg.axis()
      .scale(x_scale)
      .orient("bottom");
    this.y_axis = d3.svg.axis()
      .scale(y_scale)
      .orient("left");
    this.c_scale = d3.scale.category10();
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
    this.line = d3.svg.line()
      .interpolate("step-after")
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
  let missing_values = current_missing.map((cm) => cm.x);
  var smooth = Math.sqrt;
  var clusterer = new Clusterer(missing_values, smooth);
  var ranges = clusterer.get_ranges(4);
  let i = 0, j = 0;
  let maxcount = 1;
  let hists = ranges.map(
    ({max}) => {
      for (; j < current_missing.length && current_missing[j].x <= max; ++j) {
        continue
      }
      let rv = {
        count: 0,
        values: current_missing.slice(i, j)
      };
      rv.values.forEach(({locales}) => {
        rv.count += locales.length;
        maxcount = Math.max(maxcount, locales.length);
      });
      i=j;
      return rv;
    }
  );

  // histogram
  var hist_block = $('<div>').addClass('hist_block');
  var graphs_row = $('<tr>').addClass("hist graph")
    .append($('<td>').addClass("axis")
      .append(hist_block));
  var descs_row = $('<tr>').addClass("hist desc").append('<td>');
  $('#histogram').empty().append($('<table>').append(graphs_row).append(descs_row));
  var atitle = $('<span>').text(maxcount);
  atitle.css('position', 'absolute').css('top', '0px');
  hist_block.append(atitle);
  hist_block.css('width', atitle.css('width'));
  hist_block.css('padding-left', '1px').css('padding-right', '1px');
  // create display of histogram
  var barwidth = 7;
  var chart_height = Number(hist_block.css('height').replace('px', ''));
  function display_f(_v) {
    return Math.pow(_v, 3 / 4);
  }
  var scale = chart_height * 1.0 / display_f(maxcount);
  var hist, range, td, previous_x, _left, height;
  for (i=0; i < hists.length; ++i) {
    hist = hists[i];
    range = ranges[i];
    td = $('<td>').appendTo(descs_row);
    if (range.min === range.max) {
      td.append(range.min);
    }
    else {
      td.append(range.min + ' - ' + range.max);
    }
    td = $('<td>').attr('title', hist.count).appendTo(graphs_row);
    hist_block = $("<div>").addClass("hist_block").appendTo(td);
    previous_x = null;
    _left = 0;
    for (let {x, locales} of hist.values) {
      height = display_f(locales.length) * scale;
      if (previous_x !== null) {
        _left += (smooth(x - 1) - smooth(previous_x)) * barwidth;
      }
      $('<div>')
        .addClass('bar')
        .attr('title', x + ': ' + locales.join(' ') + ' (' + locales.length + ')')
        .css({
          top: chart_height - height + 'px',
          width: barwidth - 2 + 'px',
          height: height - 1 + 'px',
          left: Number(_left).toFixed(1) + 'px'
        })
        .appendTo(hist_block);
      previous_x = x;
      _left += barwidth;
    }
    td.css("width", Number(_left).toFixed(1) + 'px');
  }
}

renderPlot();
