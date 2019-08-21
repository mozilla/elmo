/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global d3 */

class Data {
  constructor(labels) {
    this.labels = labels;
    this._data = {};
    var _d = this._data;
    this.labels.forEach(label => {this._data[label] = 0})
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
    var v = 0, rv = {}, _d = this._data;
    if (date) rv.date = date;
    Object.assign(rv, _d);
    return rv;
  }
};

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

var data, state, data0, X;
var loc_data = LOCALE_DATA;

var dashboardHistoryUrl = window.DASHBOARD_HISTORY_URL + "&starttime=" + formatRoundedDate(startdate) + "&endtime=" + formatRoundedDate(enddate) + "&locale="

class ProgressPlot {
  constructor() {
    this.params = params;
  }

  compute_states() {
    const graphlabels = ['good', 'shady', 'bad'];
    if (this.params.top_locales) graphlabels.unshift('top_locales');
    let state = new Data(graphlabels);
    let current_states = {}, current_top_state = {};
    this.current_missing = {};
    let _getState = this._getState.bind(this);
    this.states_over_time = loc_data.map(
      (at_time) => {
        Object.assign(this.current_missing, at_time.locales);
        let changed_locales = {}, skip = true;
        Object.entries(at_time.locales).forEach(([loc, missing]) => {
          let isGood = this._getState(missing);
          if (isGood != current_states[loc]) {
            changed_locales[loc] = isGood;
            skip = false;
          }
        });
        if (params.top_locales) {
          let this_top_state = missing_after_top_locales(this.current_missing, params.top_locales);
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
    ).filter(_state => _state);
    this.states_over_time.push(state.data(enddate));
  }

  _getState(count) {
    if (count == 0) return 'good';
    if (count > this.params.bound) return 'bad';
    return 'shady';
  }
}

function renderPlot() {
  var tp = new Timeplot("#my-timeplot",
                    fullrange,
                    [startdate, enddate],
                    params);
  var svg = tp.svg;
  X = tp.x;

  var tooltipElt = document.getElementById('locales-tooltip');
  var goodLocalesElt = tooltipElt.querySelector('.good');
  var shadyLocalesElt = tooltipElt.querySelector('.shady');
  var badLocalesElt = tooltipElt.querySelector('.bad');
  var percElt = tooltipElt.querySelector('.top_locales')

  const plot = new ProgressPlot();
  data = plot;
  plot.compute_states();
  var layers = ['good', 'shady'];
  if (!params.hideBad) {
    layers.push('bad');
  }
  data0 = d3.layout.stack()(layers.map(function(k){
    return plot.states_over_time.map(function(d){
      return {
        x: d.date,
        y: d[k]
      };
    });
  }));
  var area = d3.svg.area()
    .interpolate("step-after")
    .x(function(d) {
      return tp.x(d.x);
    })
    .y0(function(d) { return tp.y(d.y0); })
    .y1(function(d) { return tp.y(d.y + d.y0); });
  tp.yDomain([0, d3.max(plot.states_over_time.map(function(d) { return d.good + d.shady + (params.hideBad ? 0: d.bad); })) + 10]);
  svg.selectAll("path.progress")
     .data(data0)
     .enter()
     .append("path")
     .attr("class", "progress")
     .style("stroke", "black")
     .style("fill", function (d, i) {
        return ['#339900', 'grey', '#990000'][i];
      })
     .attr("d", area);
  if (params.top_locales) {
      tp.y2Domain([
        0,
        d3.max(plot.states_over_time.map(function(d) { return d.top_locales.missing; })) * 1.1 + 10
        ]);
      var percLine = d3.svg.line()
      .interpolate('step-after')
        .x(function(d) {return tp.x(d.date)})
        .y(function(d) {return tp.y2(d.top_locales.missing)});
      svg.append("path")
        .attr("class", "top_locales")
        .attr("d", percLine(plot.states_over_time));
  }

  // --> Changing locales logic <-- //

  // Utility function to add a list of locales to a DOM element.
  function showLocalesInElement(locales, element) {
    var ln = locales.length;

    // Maximum number of elements that will be shown in the reduced tooltip.
    var clipTreshold = 4;

    if (ln === 0) {
      element.textContent = "-";
      return;
    }

    element.innerHTML = '';

    var clippedElt = document.createElement("span");
    clippedElt.className = "clipped";
    var addTo = element;

    for (var i = 0; i < ln; i++) {
      var locale = locales[i];

      var linkElt = document.createElement("a");
      linkElt.href= dashboardHistoryUrl + locale;
      linkElt.textContent = locale;

      if (i >= clipTreshold) {
        addTo = clippedElt;
      }

      if (i > 0) {
        addTo.appendChild(document.createTextNode(', '));
      }
      addTo.appendChild(linkElt);
    }

    element.appendChild(clippedElt);

    if (ln > clipTreshold) {
      const hellip = document.createElement("span");
      hellip.className = "hellip";
      hellip.textContent = "…";
      element.appendChild(hellip);
    }
  }

  // Create the transparent white box that follows the mouse and shows the
  // considered time range.
  var whiteBoxWidth = 20; // pixels
  var whiteBoxOffset = whiteBoxWidth / 2;
  var whiteBox = svg.append("g").append("rect");
  whiteBox.attr("x", -9999)
    .attr("y", tp.y(0) - tp.height - 1)
    .attr("width", whiteBoxWidth)
    .attr("height", tp.height)
    .style("fill", "white")
    .style("stroke", "white")
    .style("opacity", "0.2");

  // Return the latest state of each locale that changed in a time window.
  function findChanges(startTime, endTime) {
    let final_states = {}, triagedLocales = {
      good: [],
      bad: [],
      shady: []
    };
    for (let _state of plot.states_over_time) {
      if (_state.date < startTime) continue;
      if (_state.date > endTime) break;
      Object.assign(final_states, _state.changed_locales);
    }
    Object.entries(final_states).forEach(
      ([loc, endState]) => triagedLocales[endState].push(loc)
    );
    return triagedLocales;
  }

  function showTooltip() {
    whiteBox.style("opacity", 0.2);
    tooltipElt.style.display = 'block';
  }

  function hideTooltip() {
    whiteBox.style("opacity", 0);
    tooltipElt.style.display = 'none';
  }

  function showLocalesTooltip() {
    // First update the position of the white box.
    var mouseX = d3.mouse(this)[0];
    whiteBox.attr("x", mouseX - whiteBoxOffset);

    // Then compute the list of changing locales in this range.
    var triagedLocales = findChanges(
      tp.x.invert(mouseX - whiteBoxOffset),
      tp.x.invert(mouseX + whiteBoxOffset)
    );
    if (params.top_locales) {
      var date = tp.x.invert(mouseX), i = 0;
      while (plot.states_over_time[i] && plot.states_over_time[i].date < date) ++i;
      var datum = plot.states_over_time[i-1].top_locales;
      percElt.innerHTML = `${datum.missing} (<a href="${dashboardHistoryUrl + datum.locale}">${datum.locale}</a>)`;
      percElt.parentElement.style.display = '';
    }
    else {
      percElt.parentElement.style.display = 'none';
    }

    // Finaly show those locales in the tooltip box.
    if (triagedLocales) {
      showLocalesInElement(triagedLocales.good, goodLocalesElt);
      showLocalesInElement(triagedLocales.bad, badLocalesElt);
      showLocalesInElement(triagedLocales.shady, shadyLocalesElt);
    }

    if (mouseX > tp.width / 2) {
      tooltipElt.style.right = (tp.width - mouseX) + "px";
      tooltipElt.style.left = "auto";
    }
    else {
      tooltipElt.style.left = mouseX + "px";
      tooltipElt.style.right = "auto";
    }

    showTooltip();
  }
  tp.showMilestones();

  // Define a new element that is the size of the graph, and that is used to
  // detect the mouse movements. As this element is on top in the DOM, this
  // ensures all mouse events will be caught.
  var graphZone = svg.append("g").append("rect");
  graphZone.attr("x", 0)
    .attr("y", tp.y(0) - tp.height - 1)
    .attr("width", tp.width)
    .attr("height", tp.height)
    .style("opacity", 0);

  // Hide and show the tooltip and the white box.
  graphZone.on("mousemove", showLocalesTooltip)
           .on("mouseout", hideTooltip);

  tooltipElt.addEventListener("mouseover", showTooltip);
  tooltipElt.addEventListener("mouseout", hideTooltip);

  // <-- Changing locales logic --> //

  paintHistogram(plot.current_missing);
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
  paintHistogram(d, evt.controlKey || evt.metaKey);
}

let kown_graphs = [];
function paintPercentile(d, add) {
  let missing2locales = {};
  let locales = Object.keys(d);
  locales.forEach(locale => {
    let loc_list;
    const missing = d[locale];
    if (!(missing in missing2locales)) {
      missing2locales[missing] = [];
    }
    missing2locales[missing].push(locale);
  });
  let x = Object.keys(missing2locales), last=0;
  x.sort((l, r) => l - r);
  if (!add) {
    known_graphs = [];
  }
  known_graphs.push(x.map(_x => ({
    x: _x,
    locales: missing2locales[_x],
    percentile: last += missing2locales[_x].length,
  })));
  let xmargin = 40, ymargin = 40;
  let {width, height} = window.getComputedStyle(document.querySelector('#percentile'));
  width = +(width.replace('px', '')) - 2*xmargin;
  height = +(height.replace('px', '')) - 2*ymargin;
  let x_scale = d3.scale.sqrt()
      .range([0, width])
      .domain([0, x[x.length - 1] * 1.1]);
  let y_scale = d3.scale.linear()
      .range([height, 0])
      .domain([0, locales.length]);
  let c_scale = d3.scale.category10()
      .domain([0, known_graphs.length])
  let x_axis = d3.svg.axis().scale(x_scale).orient("bottom"),
    y_axis = d3.svg.axis().scale(y_scale).orient("left");
  var svg = d3.select('#percentile').html('').append("svg")
      .attr("width", width + xmargin)
      .attr("height", height + 2*ymargin)
      .append("g")
      .attr("transform", "translate(" + xmargin + "," + ymargin + ")");

  // Add the x-axis.
  svg.append("svg:g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")")
    .call(x_axis);
  // Add the y-axis.
  svg.append("svg:g")
    .attr("class", "y axis")
    .call(y_axis);
  let line = d3.svg.line()
    .interpolate("step-after")
    .x(d => x_scale(d.x))
    .y(d => y_scale(d.percentile));
  svg.selectAll("path.perc_line").data(known_graphs)
      .enter()
      .append("path")
      .attr("class", "perc_line")
      .attr("fill", "none")
      .attr("stroke", (d, i) => c_scale(i))
      .attr("stroke-width", 1.5)
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("d", line);
}

function paintHistogram(d, add) {
  paintPercentile(d, add)
  var data, loc, i;
  function numerical(a, b) {return a-b;}
  data = Object.values(d).sort(numerical);
  var smooth = Math.sqrt;
  var clusterer = new Clusterer(data, smooth);
  var ranges = clusterer.get_ranges(4); // TODO find something better
  var hists = new Array(ranges.length);
  for (i = 0; i < hists.length; ++i) hists[i] = [];
  var maxcount = 1;
  for (loc in d) {
    var val = d[loc];
    for (i = 0; i < ranges.length && val > ranges[i].max; ++i) {
    }
    if (hists[i][val]) {
      hists[i][val].push(loc);
      if (hists[i][val].length > maxcount) {
        maxcount = hists[i][val].length;
      }
    } else {
      hists[i][val] = [loc];
    }
  }

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
  var chart_height = Number(hist_block.css('height').replace('px',''));
  var display_f = function(_v) {
    return Math.pow(_v, 3 / 4);
  };
  var scale = chart_height * 1.0 / display_f(maxcount);
  var hist, range, td, values, previous_j, _left, v, height;
  function valuesForHist(h) {
    function m(v, i) {
      return v ? i : undefined;
    }
    function f(v) {return v!== undefined;}
    return h.map(m).filter(f);
  }
  for (i in hists) {
    hist = hists[i];
    range = ranges[i];
    td = $('<td>').appendTo(descs_row);
    if (range.min == range.max) {
      td.append(range.min);
    } else {
      td.append(range.min + ' - ' + range.max);
    }
    td = $('<td>').attr('title', range.count).appendTo(graphs_row);
    hist_block = $("<div>").addClass("hist_block").appendTo(td);
    values = valuesForHist(hist);
    values.sort(numerical);
    previous_j = null;
    _left = 0;
    for (var k in values) {
      j = values[k];
      v = hist[j];
      v.sort();
      height = display_f(v.length) * scale;
      if (previous_j !== null) {
        _left += (smooth(j - 1) - smooth(previous_j)) * barwidth;
      }
      $('<div>')
          .addClass('bar')
          .attr('title', j + ': ' + v.join(' ') + ' (' + v.length + ')')
          .css({
            top: chart_height - height + 'px',
            width: barwidth - 2 + 'px',
            height: height - 1 + 'px',
            left: Number(_left).toFixed(1) + 'px'
          })
          .appendTo(hist_block);
      previous_j = j;
      _left += barwidth;
    }
    td.css("width", Number(_left).toFixed(1) + 'px');
  }
}

function missing_after_top_locales(current, cut_off) {
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

renderPlot();
